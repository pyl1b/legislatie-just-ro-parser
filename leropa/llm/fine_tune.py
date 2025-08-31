"""End-to-end fine-tuning pipeline.

This module provides utilities to:
1) Obtain a text corpus (HTTP(S) URL or local path),
2) Prepare a causal-language-modeling dataset,
3) Fine-tune meta-llama/Llama-3.2-3B with LoRA/QLoRA or full precision,
4) Merge adapters (if used) and save full HF weights,
5) Convert the HF model to GGUF using llama.cpp,
6) Build an Ollama model by generating a Modelfile and calling `ollama create`.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence, cast

import bitsandbytes as bnb  # noqa: F401
import torch
from attrs import asdict, define
from peft import LoraConfig, PeftModel, get_peft_model
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,  # CLM when mlm=False
    PreTrainedModel,
    PreTrainedTokenizerBase,
    Trainer,
    TrainingArguments,
)


@define(slots=True)
class PipelineConfig:
    """Top-level configuration for the pipeline.

    Attributes:
        model_id: Hugging Face repo id for the base model.
        output_dir: Where to write HF weights, GGUF and Modelfile.
        corpus_url: HTTP(S) URL to a UTF-8 text file, or empty to use
            ``local_corpus``.
        local_corpus: Local file or directory with ``.txt`` files.
        seq_len: Sequence length for CLM training windows.
        stride: Stride between windows (token-level).
        train_epochs: Number of fine-tuning epochs.
        batch_size: Per-device train batch size.
        learning_rate: Optimizer learning rate.
        use_qlora: Whether to use QLoRA (requires GPU + bitsandbytes).
        lora_r: LoRA rank.
        lora_alpha: LoRA alpha.
        lora_dropout: LoRA dropout probability.
        gguf_outtype: GGUF outtype to produce (e.g. ``f16``, ``q8_0``).
        ollama_model_name: Name to register the model under in Ollama.
        ollama_context: Optional context length for Modelfile (0 = default).
        system_prompt: Optional system prompt to include in Modelfile.
        hf_token_env: Env var name with a valid HF token (if required).
        max_corpus_chars: Hard cap on chars to read from corpus (0 disables).
        save_steps: Trainer save/checkpoint steps.
    """

    model_id: str = "meta-llama/Llama-3.2-3B"
    output_dir: str = "llama32_memorizer_out"
    corpus_url: str = ""
    local_corpus: str = ""
    seq_len: int = 4096
    stride: int = 4096
    train_epochs: int = 1
    batch_size: int = 1
    learning_rate: float = 2e-5
    use_qlora: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    gguf_outtype: str = "q8_0"
    ollama_model_name: str = "llama32-custom"
    ollama_context: int = 0
    system_prompt: str = ""
    hf_token_env: str = "HUGGINGFACE_HUB_TOKEN"
    max_corpus_chars: int = 0
    save_steps: int = 0


class StreamingCLMDataset(Dataset):
    """A minimal streaming CLM dataset that tokenizes a big text into windows.

    Attributes:
        input_ids: Token id tensor for the entire concatenated corpus.
        attention_mask: Attention mask tensor aligned with input_ids.
        seq_len: Window length.
        stride: Step between consecutive windows.
        n_windows: Number of (input, label) windows addressable.
    """

    def __init__(
        self,
        tokenizer: PreTrainedTokenizerBase,
        text: str,
        seq_len: int,
        stride: int,
    ) -> None:
        """Tokenize the text and build sliding windows.

        Args:
            tokenizer: HF tokenizer compatible with the base model.
            text: Raw UTF-8 text to train on.
            seq_len: Target sequence length (window length).
            stride: Stride between window starts.

        Throws:
            ValueError: If seq_len or stride are invalid.

        Returns:
            None
        """
        if seq_len <= 0 or stride <= 0:
            raise ValueError("seq_len and stride must be positive.")

        # Tokenize once; use EOS as pad per CLM best practice.
        enc = tokenizer(
            text,
            return_tensors="pt",
            return_attention_mask=True,
            add_special_tokens=False,
        )
        input_ids_t = cast("torch.Tensor", enc["input_ids"])
        attn_mask_t = cast("torch.Tensor", enc["attention_mask"])
        self.input_ids = input_ids_t.squeeze(0)
        self.attention_mask = attn_mask_t.squeeze(0)
        self.seq_len = int(seq_len)
        self.stride = int(stride)
        total = self.input_ids.shape[0]
        self.n_windows = max(0, 1 + (total - self.seq_len) // self.stride)

    def __len__(self) -> int:
        """Number of CLM windows.

        Returns:
            Integer window count.
        """
        return self.n_windows

    def __getitem__(self, idx: int) -> dict:
        """Slice a single window for CLM (labels = input_ids).

        Args:
            idx: Window index.

        Throws:
            IndexError: If index is out of range.

        Returns:
            Dict with 'input_ids', 'attention_mask', 'labels'.
        """
        if idx < 0 or idx >= self.n_windows:
            raise IndexError("Index out of range")

        start = idx * self.stride
        end = start + self.seq_len
        ids = self.input_ids[start:end]
        mask = self.attention_mask[start:end]
        return {
            "input_ids": ids,
            "attention_mask": mask,
            "labels": ids.clone(),
        }


def run(cmd: Sequence[str], cwd: Optional[str] = None) -> None:
    """Run a shell command and stream output.

    Args:
        cmd: The command and its arguments.
        cwd: Optional working directory.

    Throws:
        RuntimeError: If the command returns non-zero.

    Returns:
        None
    """
    print(f"[cmd] {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(
            f"Command failed with exit code {ret}: {' '.join(cmd)}"
        )


def obtain_text(corpus_url: str, local_path: str, cap_chars: int = 0) -> str:
    """Load or download a UTF-8 text corpus.

    If both corpus_url and local_path are provided, the corpus_url is used only
    if the local path does not exist (the file is downloaded to the local
    path).

    Args:
        corpus_url: HTTP(S) URL to a text file (if provided).
        local_path: Local file or directory path.
        cap_chars: If >0, truncate text to this many characters.

    Throws:
        FileNotFoundError: If neither URL nor local data exist.
        RuntimeError: If HTTP download fails.

    Returns:
        The raw text.
    """
    p: Path | None = None
    if local_path and corpus_url:
        p = Path(local_path)
        if p.exists():
            corpus_url = ""

    if corpus_url:
        import urllib.request

        try:
            with urllib.request.urlopen(corpus_url) as r:
                raw = r.read().decode("utf-8", errors="ignore")
            if local_path:
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(raw)
        except Exception as e:
            raise RuntimeError(f"failed to download {corpus_url}: {e}") from e
        text = raw
    else:
        if p is None:
            p = Path(local_path)
        if not p.exists():
            raise FileNotFoundError(
                f"local corpus path not found: {local_path}"
            )

        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="ignore")
        else:
            # Concatenate all text files in a directory (non-recursive)
            parts = []
            for f in sorted(list(p.glob("*.txt")) + list(p.glob("*.md"))):
                parts.append(f.read_text(encoding="utf-8", errors="ignore"))
            text = "\n".join(parts)

    if cap_chars > 0:
        text = text[:cap_chars]
    return text


def load_tokenizer(
    model_id: str, hf_token_env: str
) -> PreTrainedTokenizerBase:
    """Load tokenizer and set CLM-friendly padding.

    Args:
        model_id: HF model id.
        hf_token_env: Name of env var with a valid HF token.

    Throws:
        EnvironmentError: If model requires auth and token is missing.

    Returns:
        A configured tokenizer.
    """
    token = os.environ.get(hf_token_env, None)
    tok_kwargs: dict[str, object] = {"use_fast": True}
    if token:
        tok_kwargs["token"] = token
    tok = AutoTokenizer.from_pretrained(model_id, **tok_kwargs)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token  # CLM recipe
    return tok


def load_model_for_training(
    cfg: PipelineConfig, tokenizer: PreTrainedTokenizerBase
) -> PreTrainedModel:
    """Instantiate base model for CLM fine-tuning with optional QLoRA.

    Args:
        cfg: Pipeline configuration.
        tokenizer: Tokenizer loaded for this model.

    Returns:
        A Transformers CausalLM (possibly PEFT-wrapped).
    """
    token = os.environ.get(cfg.hf_token_env, None)
    common = dict(
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=False,
    )
    if token:
        common["token"] = token

    if cfg.use_qlora:
        model = AutoModelForCausalLM.from_pretrained(
            cfg.model_id,
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            **common,
        )
        # Typical LoRA target modules for Llama-family
        target_modules = [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
        lconf = LoraConfig(
            r=cfg.lora_r,
            lora_alpha=cfg.lora_alpha,
            lora_dropout=cfg.lora_dropout,
            target_modules=target_modules,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lconf)
    else:
        # Full precision (or bf16/fp16 auto) fine-tune
        model = AutoModelForCausalLM.from_pretrained(cfg.model_id, **common)

    # Align pad token id with tokenizer
    pad_id = getattr(tokenizer, "pad_token_id", None)
    if pad_id is not None:
        model.config.pad_token_id = int(pad_id)
    model.config.use_cache = False  # better for training
    return model


def make_dataset(
    tokenizer: PreTrainedTokenizerBase,
    text: str,
    seq_len: int,
    stride: int,
) -> StreamingCLMDataset:
    """Create a CLM dataset from raw text.

    Args:
        tokenizer: Tokenizer to apply.
        text: Raw text content.
        seq_len: Target sequence length.
        stride: Sliding window stride.

    Returns:
        A Dataset yielding CLM training items.
    """
    return StreamingCLMDataset(tokenizer, text, seq_len, stride)


def train_clm(
    cfg: PipelineConfig,
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizerBase,
    dataset: Dataset,
) -> Path:
    """Fine-tune the model on the dataset using Transformers Trainer.

    Args:
        cfg: Pipeline configuration.
        model: Model to train (possibly PEFT-wrapped).
        tokenizer: Tokenizer for padding & collation.
        dataset: Training dataset.

    Returns:
        Path to the directory containing the trained model (HF format).
    """
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    run_name = "clm-finetune"
    save_dir = out / "hf_checkpoints"

    # Use DataCollatorForLanguageModeling with mlm=False (CLM)
    # per HF docs (labels=inputs, shift handled internally by model).
    # Ref docs: CLM & collators.
    data_collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

    args = TrainingArguments(
        output_dir=str(save_dir),
        per_device_train_batch_size=cfg.batch_size,
        gradient_accumulation_steps=max(1, 8 // cfg.batch_size),
        num_train_epochs=cfg.train_epochs,
        learning_rate=cfg.learning_rate,
        logging_steps=50,
        save_steps=cfg.save_steps,
        bf16=torch.cuda.is_available(),
        report_to=[],
        run_name=run_name,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        data_collator=data_collator,
    )
    trainer.train()

    # If PEFT/LoRA used, merge for standalone HF weights.
    if cfg.use_qlora:
        if isinstance(model, PeftModel):
            merged = model.merge_and_unload()  # type: ignore[attr-defined]
            merged.save_pretrained(  # type: ignore[attr-defined]
                str(out / "hf_merged"),
                safe_serialization=True,
            )
            tokenizer.save_pretrained(  # type: ignore[attr-defined]
                str(out / "hf_merged"),
            )
            return out / "hf_merged"

    # Otherwise, save the trained full model as-is
    final_dir = out / "hf_full"
    model.save_pretrained(  # type: ignore[attr-defined]
        str(final_dir),
        safe_serialization=True,
    )
    tokenizer.save_pretrained(  # type: ignore[attr-defined]
        str(final_dir)
    )
    return final_dir


def ensure_llama_cpp(repo_dir: Path) -> None:
    """Clone llama.cpp if needed and install Python deps for conversion.

    Args:
        repo_dir: Target directory to clone/build in.

    Throws:
        RuntimeError: If git/pip operations fail.

    Returns:
        None
    """
    if not repo_dir.exists():
        run(
            [
                "git",
                "clone",
                "https://github.com/ggerganov/llama.cpp",
                str(repo_dir),
            ]
        )
    # Install python requirements for converters
    req = repo_dir / "requirements.txt"
    if req.exists():
        run([sys.executable, "-m", "pip", "install", "-r", str(req)])


def convert_to_gguf(
    hf_dir: Path, gguf_out: Path, outtype: str, llama_cpp_dir: Path
) -> Path:
    """Convert an HF CausalLM directory into a GGUF using llama.cpp.

    Args:
        hf_dir: Directory with HF safetensors + config.json + tokenizer files.
        gguf_out: Path to the desired .gguf output file.
        outtype: Desired outtype (e.g., 'f16', 'q8_0').
        llama_cpp_dir: Path to local llama.cpp repo (must contain
            ``convert_hf_to_gguf.py``).

    Throws:
        FileNotFoundError: If converter script not found.

    Returns:
        Path to the GGUF file.
    """
    conv = llama_cpp_dir / "convert_hf_to_gguf.py"
    if not conv.exists():
        raise FileNotFoundError(
            "convert_hf_to_gguf.py not found in llama.cpp repo"
        )

    gguf_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(conv),
        str(hf_dir),
        "--outfile",
        str(gguf_out),
        "--outtype",
        outtype,
    ]
    run(cmd)
    return gguf_out


def write_modelfile(
    gguf_path: Path, model_name: str, ctx: int = 0, system: str = ""
) -> Path:
    """Write a minimal Ollama Modelfile that imports the GGUF.

    Args:
        gguf_path: Local path to the .gguf file.
        model_name: Model name (used for logging only).
        ctx: If >0, include a PARAMETER num_ctx.
        system: Optional system prompt text.

    Returns:
        Path to the created Modelfile.
    """
    lines = [f"FROM {gguf_path}"]
    if ctx > 0:
        lines.append(f"PARAMETER num_ctx {ctx}")
    if system.strip():
        # triple-quote block
        block = '"""\n' + system.strip() + '\n"""'
        lines.append(f"SYSTEM {block}")
    content = "\n".join(lines) + "\n"

    modelfile = gguf_path.parent / "Modelfile"
    modelfile.write_text(content, encoding="utf-8")
    print(f"[info] Wrote Modelfile for {model_name}:\n{content}")
    return modelfile


def create_ollama_model(modelfile: Path, model_name: str) -> None:
    """Create or overwrite an Ollama model using a Modelfile.

    Args:
        modelfile: Path to Modelfile.
        model_name: Target name registered in Ollama.

    Throws:
        RuntimeError: If `ollama create` fails.

    Returns:
        None
    """
    run(["ollama", "create", model_name, "-f", str(modelfile)])


def run_pipeline(
    *,
    corpus_url: str = "",
    local_corpus: str = "",
    output_dir: str = "llama32_memorizer_out",
    epochs: int = 1,
    use_qlora: Optional[bool] = None,
    gguf_outtype: str = "q8_0",
    ollama_name: str = "llama32-custom",
    ollama_ctx: int = 0,
    system_prompt: str = "",
    cap_chars: int = 0,
) -> None:
    """Run the fine-tuning and conversion pipeline.

    Args:
        corpus_url: HTTP(S) URL to a UTF-8 text corpus.
        local_corpus: Local file or directory with .txt files.
        output_dir: Output directory for all artifacts.
        epochs: Number of training epochs.
        use_qlora: Force enable/disable QLoRA. If None, use default.
        gguf_outtype: GGUF outtype (e.g. "f16", "q8_0").
        ollama_name: Name for the Ollama model.
        ollama_ctx: PARAMETER num_ctx in Modelfile (0 omits it).
        system_prompt: Optional system prompt embedded in Modelfile.
        cap_chars: Cap characters loaded from corpus (0 = all).

    Returns:
        None
    """
    cfg = PipelineConfig()
    cfg.output_dir = output_dir or cfg.output_dir
    cfg.corpus_url = corpus_url or cfg.corpus_url
    cfg.local_corpus = local_corpus or cfg.local_corpus
    cfg.train_epochs = int(epochs) if epochs else cfg.train_epochs
    cfg.gguf_outtype = gguf_outtype or cfg.gguf_outtype
    cfg.ollama_model_name = ollama_name or cfg.ollama_model_name
    cfg.ollama_context = int(ollama_ctx)
    cfg.system_prompt = system_prompt or cfg.system_prompt
    cfg.max_corpus_chars = int(cap_chars)

    if use_qlora is True:
        cfg.use_qlora = True
    elif use_qlora is False:
        cfg.use_qlora = False

    print("[config]", json.dumps(asdict(cfg), indent=2))

    text = obtain_text(
        cfg.corpus_url, cfg.local_corpus, cap_chars=cfg.max_corpus_chars
    )
    print(f"[info] Corpus chars: {len(text):,}")

    tok = load_tokenizer(cfg.model_id, cfg.hf_token_env)
    ds = make_dataset(tok, text, cfg.seq_len, cfg.stride)
    print(
        (
            f"[info] Windows: {len(ds):,}  "
            f"(seq_len={cfg.seq_len}, stride={cfg.stride})"
        )
    )

    model = load_model_for_training(cfg, tok)
    hf_dir = train_clm(cfg, model, tok, ds)

    llama_cpp_dir = Path(cfg.output_dir) / "llama.cpp"
    ensure_llama_cpp(llama_cpp_dir)
    gguf_path = (
        Path(cfg.output_dir)
        / f"{cfg.ollama_model_name}.{cfg.gguf_outtype}.gguf"
    )
    convert_to_gguf(hf_dir, gguf_path, cfg.gguf_outtype, llama_cpp_dir)
    print(f"[ok] GGUF written to: {gguf_path}")

    modelfile = write_modelfile(
        gguf_path, cfg.ollama_model_name, cfg.ollama_context, cfg.system_prompt
    )
    create_ollama_model(modelfile, cfg.ollama_model_name)
    print(
        (
            f"[done] Ollama model ready: {cfg.ollama_model_name}\n"
            f"- Run:  ollama run {cfg.ollama_model_name}"
        )
    )
