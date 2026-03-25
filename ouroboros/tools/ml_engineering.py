import json
import math
import cmath
from ouroboros.tools.registry import ToolEntry


def _j(obj):
    return json.dumps(obj, indent=2)


# --- 1. train_model_config ---
def _train_model_config(args: dict, ctx):
    model_type = args.get("model_type", "classification")
    framework = args.get("framework", "pytorch")
    dataset_size = args.get("dataset_size", 10000)
    presets = {
        "classification": {"lr": 1e-3, "batch_size": 64, "epochs": 50, "optimizer": "adam", "scheduler": "cosine", "weight_decay": 1e-4, "loss": "cross_entropy"},
        "regression": {"lr": 1e-3, "batch_size": 32, "epochs": 100, "optimizer": "adam", "scheduler": "reduce_on_plateau", "weight_decay": 1e-5, "loss": "mse"},
        "nlp": {"lr": 2e-5, "batch_size": 16, "epochs": 3, "optimizer": "adamw", "scheduler": "linear_warmup", "weight_decay": 0.01, "loss": "cross_entropy", "warmup_steps": 500, "max_seq_length": 512},
        "vision": {"lr": 1e-4, "batch_size": 32, "epochs": 30, "optimizer": "sgd", "scheduler": "cosine", "weight_decay": 5e-4, "loss": "cross_entropy", "momentum": 0.9},
    }
    cfg = presets.get(model_type, presets["classification"])
    if dataset_size > 100000:
        cfg["batch_size"] = min(cfg["batch_size"] * 4, 512)
    cfg.update({"model_type": model_type, "framework": framework, "dataset_size": dataset_size, "gradient_clipping": 1.0, "early_stopping_patience": 5, "mixed_precision": dataset_size > 50000})
    return f"Training config for {model_type} ({framework}):\n```json\n{_j(cfg)}\n```"


# --- 2. dataset_prep ---
def _dataset_prep(args: dict, ctx):
    data_type = args.get("data_type", "tabular")
    task = args.get("task", "classification")
    split_ratio = args.get("split_ratio", "0.8/0.1/0.1")
    pipelines = {
        "tabular": {"steps": ["drop_duplicates", "handle_missing (median/mode)", "encode_categoricals (label/onehot)", "normalize (standard_scaler)", "feature_selection (variance_threshold)", "split"], "augmentation": "SMOTE for imbalanced classes"},
        "text": {"steps": ["lowercase", "remove_html_tags", "tokenize", "remove_stopwords", "lemmatize", "encode (BPE/WordPiece)", "pad/truncate", "split"], "augmentation": "back_translation, synonym_replacement, random_insertion"},
        "image": {"steps": ["resize", "normalize (ImageNet mean/std)", "convert_to_tensor", "split"], "augmentation": "random_crop, horizontal_flip, color_jitter, rotation, cutout, mixup"},
        "audio": {"steps": ["resample (16kHz)", "extract_mel_spectrogram", "normalize", "pad/truncate", "split"], "augmentation": "time_stretch, pitch_shift, add_noise, spec_augment"},
    }
    pipeline = pipelines.get(data_type, pipelines["tabular"])
    pipeline["split_ratio"] = split_ratio
    pipeline["data_type"] = data_type
    pipeline["task"] = task
    pipeline["seed"] = 42
    pipeline["stratify"] = task == "classification"
    return f"Data prep pipeline for {data_type} ({task}):\n```json\n{_j(pipeline)}\n```"


# --- 3. model_architecture ---
def _model_architecture(args: dict, ctx):
    arch_type = args.get("architecture", "transformer")
    input_shape = args.get("input_shape", "varies")
    num_classes = args.get("num_classes", 10)
    archs = {
        "cnn": {"layers": [
            {"type": "Conv2d", "filters": 32, "kernel": 3, "activation": "relu"},
            {"type": "BatchNorm2d"}, {"type": "MaxPool2d", "kernel": 2},
            {"type": "Conv2d", "filters": 64, "kernel": 3, "activation": "relu"},
            {"type": "BatchNorm2d"}, {"type": "MaxPool2d", "kernel": 2},
            {"type": "Conv2d", "filters": 128, "kernel": 3, "activation": "relu"},
            {"type": "AdaptiveAvgPool2d", "output": 1},
            {"type": "Flatten"}, {"type": "Dropout", "p": 0.5},
            {"type": "Linear", "out": num_classes}
        ]},
        "rnn": {"layers": [
            {"type": "Embedding", "dim": 256},
            {"type": "LSTM", "hidden": 512, "layers": 2, "bidirectional": True, "dropout": 0.3},
            {"type": "Linear", "out": 256, "activation": "relu"},
            {"type": "Dropout", "p": 0.5},
            {"type": "Linear", "out": num_classes}
        ]},
        "transformer": {"config": {
            "d_model": 512, "n_heads": 8, "n_layers": 6, "d_ff": 2048,
            "dropout": 0.1, "max_seq_len": 512, "vocab_size": 30000,
            "positional_encoding": "sinusoidal", "output_head": "classification",
            "num_classes": num_classes
        }},
        "gan": {"generator": [
            {"type": "Linear", "in": 100, "out": 256}, {"type": "BatchNorm1d"}, {"type": "ReLU"},
            {"type": "Linear", "out": 512}, {"type": "BatchNorm1d"}, {"type": "ReLU"},
            {"type": "Linear", "out": 1024}, {"type": "Tanh"}
        ], "discriminator": [
            {"type": "Linear", "in": 1024, "out": 512}, {"type": "LeakyReLU", "slope": 0.2},
            {"type": "Linear", "out": 256}, {"type": "LeakyReLU", "slope": 0.2},
            {"type": "Linear", "out": 1}, {"type": "Sigmoid"}
        ]},
        "vae": {"encoder": [
            {"type": "Linear", "out": 512, "activation": "relu"},
            {"type": "Linear_mu", "out": 64}, {"type": "Linear_logvar", "out": 64}
        ], "decoder": [
            {"type": "Linear", "in": 64, "out": 512, "activation": "relu"},
            {"type": "Linear", "out": 1024, "activation": "sigmoid"}
        ], "latent_dim": 64},
        "diffusion": {"config": {
            "type": "UNet", "channels": [64, 128, 256, 512], "time_embedding_dim": 256,
            "num_res_blocks": 2, "attention_resolutions": [16, 8], "timesteps": 1000,
            "beta_schedule": "linear", "beta_start": 1e-4, "beta_end": 0.02
        }},
    }
    arch = archs.get(arch_type, archs["transformer"])
    arch["architecture"] = arch_type
    arch["input_shape"] = input_shape
    return f"Architecture: {arch_type}\n```json\n{_j(arch)}\n```"


# --- 4. hyperparameter_search ---
def _hyperparameter_search(args: dict, ctx):
    method = args.get("method", "bayesian")
    model_type = args.get("model_type", "classification")
    budget = args.get("budget", 50)
    search = {
        "method": method, "budget": budget, "model_type": model_type,
        "parameter_space": {
            "learning_rate": {"type": "log_uniform", "low": 1e-5, "high": 1e-1},
            "batch_size": {"type": "categorical", "values": [16, 32, 64, 128, 256]},
            "weight_decay": {"type": "log_uniform", "low": 1e-6, "high": 1e-2},
            "dropout": {"type": "uniform", "low": 0.0, "high": 0.5},
            "optimizer": {"type": "categorical", "values": ["adam", "adamw", "sgd"]},
            "hidden_dim": {"type": "categorical", "values": [128, 256, 512, 1024]},
        },
        "objective": "minimize_val_loss",
        "early_stopping_rounds": 10,
    }
    if method == "bayesian":
        search["acquisition_function"] = "expected_improvement"
        search["n_initial_points"] = min(10, budget // 3)
    elif method == "grid":
        search["note"] = "Warning: grid search scales exponentially with parameters"
    return f"Hyperparameter search ({method}, budget={budget}):\n```json\n{_j(search)}\n```"


# --- 5. llm_fine_tune ---
def _llm_fine_tune(args: dict, ctx):
    method = args.get("method", "lora")
    base_model = args.get("base_model", "meta-llama/Llama-3-8B")
    dataset_format = args.get("dataset_format", "alpaca")
    configs = {
        "lora": {"peft_type": "LORA", "r": 16, "lora_alpha": 32, "lora_dropout": 0.05, "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"], "bias": "none", "task_type": "CAUSAL_LM"},
        "qlora": {"peft_type": "LORA", "r": 64, "lora_alpha": 16, "lora_dropout": 0.1, "quantization": {"bits": 4, "type": "nf4", "double_quant": True, "compute_dtype": "bfloat16"}, "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]},
        "full": {"full_fine_tune": True, "gradient_checkpointing": True, "deepspeed_stage": 3, "offload_optimizer": True},
    }
    formats = {
        "alpaca": {"template": {"instruction": "...", "input": "...", "output": "..."}, "example": {"instruction": "Summarize the text", "input": "Long article...", "output": "Summary..."}},
        "sharegpt": {"template": {"conversations": [{"from": "human", "value": "..."}, {"from": "gpt", "value": "..."}]}},
        "jsonl": {"template": {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}},
    }
    cfg = configs.get(method, configs["lora"])
    cfg.update({"base_model": base_model, "training": {"lr": 2e-4, "epochs": 3, "batch_size": 4, "gradient_accumulation_steps": 8, "warmup_ratio": 0.03, "max_seq_length": 2048, "bf16": True}, "dataset_format": formats.get(dataset_format, formats["alpaca"])})
    return f"Fine-tuning config ({method}) for {base_model}:\n```json\n{_j(cfg)}\n```"


# --- 6. llm_prompt_engineer ---
def _llm_prompt_engineer(args: dict, ctx):
    style = args.get("style", "system")
    task = args.get("task", "general assistant")
    templates = {
        "system": f"You are a specialized AI assistant for {task}. Follow these guidelines:\n1. Be precise and factual\n2. Ask clarifying questions when the request is ambiguous\n3. Structure responses clearly with headers and bullet points\n4. Cite sources when making factual claims\n5. Acknowledge limitations honestly",
        "few_shot": f"Task: {task}\n\nExample 1:\nInput: [example input]\nOutput: [example output]\n\nExample 2:\nInput: [example input]\nOutput: [example output]\n\nNow process:\nInput: {{user_input}}\nOutput:",
        "chain_of_thought": f"Task: {task}\n\nLet's solve this step by step:\n1. First, identify the key components of the problem\n2. Analyze each component systematically\n3. Consider edge cases and constraints\n4. Synthesize findings into a coherent answer\n\nProblem: {{user_input}}\n\nStep-by-step reasoning:",
        "tool_use": f'{{"tools": [{{"name": "search", "description": "Search a knowledge base", "parameters": {{"query": {{"type": "string"}}}}}}, {{"name": "calculate", "description": "Perform calculations", "parameters": {{"expression": {{"type": "string"}}}}}}], "system": "You are a {task} assistant with access to tools. Use tools when needed to provide accurate answers."}}',
        "react": f"Task: {task}\n\nUse the ReAct framework:\nThought: [reasoning about what to do]\nAction: [tool_name(params)]\nObservation: [result]\n... (repeat as needed)\nAnswer: [final answer]",
    }
    prompt = templates.get(style, templates["system"])
    return f"Prompt template ({style}) for '{task}':\n```\n{prompt}\n```\n\nTips:\n- Test with diverse inputs\n- Iterate based on failure cases\n- Keep system prompts concise but specific\n- Use delimiters (```, ---) to separate sections"


# --- 7. eval_framework ---
def _eval_framework(args: dict, ctx):
    task = args.get("task", "classification")
    metrics_map = {
        "classification": ["accuracy", "precision", "recall", "f1_score", "auc_roc", "confusion_matrix", "classification_report"],
        "regression": ["mse", "rmse", "mae", "r2_score", "mape", "explained_variance"],
        "nlp_generation": ["bleu", "rouge_1", "rouge_2", "rouge_l", "meteor", "bertscore"],
        "language_model": ["perplexity", "cross_entropy_loss", "token_accuracy", "bits_per_character"],
        "object_detection": ["mAP@0.5", "mAP@0.5:0.95", "precision", "recall", "inference_fps"],
        "ranking": ["ndcg", "mrr", "map", "precision@k", "recall@k", "hit_rate"],
    }
    metrics = metrics_map.get(task, metrics_map["classification"])
    framework = {
        "task": task, "metrics": metrics,
        "evaluation_strategy": {"cross_validation": {"folds": 5, "stratified": task == "classification"}, "test_set": True, "bootstrap_ci": {"n_iterations": 1000, "confidence": 0.95}},
        "reporting": {"save_predictions": True, "generate_plots": True, "log_to": "wandb"},
    }
    return f"Evaluation framework for {task}:\n```json\n{_j(framework)}\n```"


# --- 8. rag_pipeline ---
def _rag_pipeline(args: dict, ctx):
    doc_type = args.get("doc_type", "pdf")
    embedding_model = args.get("embedding_model", "text-embedding-3-small")
    retriever = args.get("retriever", "vector")
    pipeline = {
        "ingestion": {"loader": {"pdf": "PyPDFLoader", "html": "BeautifulSoup", "markdown": "MarkdownParser", "code": "TreeSitterParser"}.get(doc_type, "UnstructuredLoader"), "chunking": {"strategy": "recursive", "chunk_size": 512, "chunk_overlap": 50, "separators": ["\n\n", "\n", ". ", " "]}},
        "embedding": {"model": embedding_model, "dimension": 1536, "batch_size": 100},
        "vector_store": {"engine": "chroma", "distance_metric": "cosine", "index_type": "hnsw"},
        "retrieval": {"method": retriever, "top_k": 5, "reranker": {"model": "cross-encoder/ms-marco-MiniLM-L-6-v2", "top_n": 3} if retriever == "vector" else None},
        "generation": {"context_window": 4096, "prompt_template": "Answer based on the context below.\n\nContext:\n{context}\n\nQuestion: {question}\nAnswer:"},
    }
    if retriever == "hybrid":
        pipeline["retrieval"]["bm25_weight"] = 0.3
        pipeline["retrieval"]["vector_weight"] = 0.7
    return f"RAG pipeline ({doc_type}, {retriever}):\n```json\n{_j(pipeline)}\n```"


# --- 9. model_deploy ---
def _model_deploy(args: dict, ctx):
    method = args.get("method", "fastapi")
    model_type = args.get("model_type", "llm")
    quantization = args.get("quantization", None)
    configs = {
        "fastapi": {"framework": "FastAPI", "config": {"workers": 4, "host": "0.0.0.0", "port": 8000, "endpoint": "/v1/predict", "batch_inference": True, "max_batch_size": 32, "timeout": 30, "health_check": "/health"}},
        "vllm": {"engine": "vLLM", "config": {"tensor_parallel_size": 1, "gpu_memory_utilization": 0.9, "max_model_len": 4096, "port": 8000, "api_format": "openai_compatible", "dtype": "auto"}},
        "tgi": {"engine": "text-generation-inference", "config": {"max_input_length": 2048, "max_total_tokens": 4096, "max_batch_prefill_tokens": 4096, "port": 8080, "sharded": False}},
        "onnx": {"export": {"opset_version": 17, "dynamic_axes": True, "optimize": True}, "runtime": "onnxruntime", "providers": ["CUDAExecutionProvider", "CPUExecutionProvider"]},
    }
    cfg = configs.get(method, configs["fastapi"])
    cfg["model_type"] = model_type
    if quantization:
        quant_cfgs = {
            "gptq": {"bits": 4, "group_size": 128, "desc_act": True, "method": "GPTQ"},
            "awq": {"bits": 4, "group_size": 128, "method": "AWQ", "zero_point": True},
            "gguf": {"bits": 4, "type": "Q4_K_M", "method": "GGUF", "use_llama_cpp": True},
        }
        cfg["quantization"] = quant_cfgs.get(quantization, {"bits": 4, "method": quantization})
    cfg["docker"] = {"base_image": "nvidia/cuda:12.1-runtime", "expose_port": cfg.get("config", {}).get("port", 8000)}
    return f"Deployment config ({method}):\n```json\n{_j(cfg)}\n```"


# --- 10. training_monitor ---
def _training_monitor(args: dict, ctx):
    backend = args.get("backend", "wandb")
    metrics = args.get("metrics", ["loss", "accuracy"])
    dashboard = {
        "backend": backend, "project": "my-training-run",
        "panels": [
            {"title": "Loss Curves", "metrics": ["train/loss", "val/loss"], "type": "line", "x_axis": "step"},
            {"title": "Learning Rate", "metrics": ["lr"], "type": "line", "x_axis": "step"},
            {"title": "Gradient Norms", "metrics": ["grad_norm", "grad_norm_clipped"], "type": "line"},
            {"title": "GPU Utilization", "metrics": ["gpu_mem_used", "gpu_utilization"], "type": "line"},
        ],
        "alerts": [{"condition": "val/loss > train/loss * 2", "message": "Possible overfitting"}, {"condition": "grad_norm > 10", "message": "Gradient explosion detected"}, {"condition": "lr < 1e-7", "message": "Learning rate too small"}],
        "checkpointing": {"save_every_n_steps": 500, "keep_top_k": 3, "monitor": "val/loss", "mode": "min"},
        "logging": {"log_every_n_steps": 10, "log_gradients": True, "log_parameters": True},
    }
    for m in metrics:
        if m not in ["loss", "accuracy"]:
            dashboard["panels"].append({"title": m, "metrics": [f"train/{m}", f"val/{m}"], "type": "line"})
    return f"Training monitor config ({backend}):\n```json\n{_j(dashboard)}\n```"


# --- 11. quantum_circuit ---
def _quantum_circuit(args: dict, ctx):
    algorithm = args.get("algorithm", "grover")
    n_qubits = args.get("n_qubits", 3)
    circuits = {
        "grover": {"description": f"Grover's search on {n_qubits} qubits", "steps": [
            {"gate": "H", "targets": list(range(n_qubits)), "note": "superposition"},
            {"gate": "Oracle", "type": "phase_flip", "marked_state": "1" * n_qubits},
            {"gate": "H", "targets": list(range(n_qubits))},
            {"gate": "X", "targets": list(range(n_qubits))},
            {"gate": "MCZ", "controls": list(range(n_qubits - 1)), "target": n_qubits - 1},
            {"gate": "X", "targets": list(range(n_qubits))},
            {"gate": "H", "targets": list(range(n_qubits))},
            {"gate": "Measure", "targets": list(range(n_qubits))},
        ], "iterations": max(1, int(math.pi / 4 * math.sqrt(2 ** n_qubits)))},
        "shor": {"description": f"Shor's algorithm structure ({n_qubits} qubits)", "steps": [
            {"gate": "H", "targets": list(range(n_qubits // 2)), "note": "QFT register"},
            {"gate": "ControlledModExp", "note": "modular exponentiation"},
            {"gate": "QFT_inverse", "targets": list(range(n_qubits // 2))},
            {"gate": "Measure", "targets": list(range(n_qubits // 2))},
        ]},
        "vqe": {"description": "Variational Quantum Eigensolver", "steps": [
            {"gate": "RY", "targets": list(range(n_qubits)), "params": "theta_i"},
            {"gate": "CNOT", "pairs": [[i, i + 1] for i in range(n_qubits - 1)]},
            {"gate": "RY", "targets": list(range(n_qubits)), "params": "phi_i"},
            {"gate": "Measure", "basis": "Z", "targets": list(range(n_qubits))},
        ], "optimizer": "COBYLA", "ansatz": "RealAmplitudes"},
        "qaoa": {"description": "QAOA for MaxCut", "steps": [
            {"gate": "H", "targets": list(range(n_qubits))},
            {"gate": "ZZ", "pairs": "graph_edges", "param": "gamma"},
            {"gate": "RX", "targets": list(range(n_qubits)), "param": "beta"},
            {"gate": "Measure", "targets": list(range(n_qubits))},
        ], "layers": 2},
    }
    circuit = circuits.get(algorithm, circuits["grover"])
    circuit["n_qubits"] = n_qubits
    return f"Quantum circuit ({algorithm}, {n_qubits} qubits):\n```json\n{_j(circuit)}\n```"


# --- 12. quantum_simulation ---
def _quantum_simulation(args: dict, ctx):
    operation = args.get("operation", "hadamard")
    initial_state = args.get("initial_state", "0")
    gates = {
        "hadamard": [[1 / math.sqrt(2), 1 / math.sqrt(2)], [1 / math.sqrt(2), -1 / math.sqrt(2)]],
        "pauli_x": [[0, 1], [1, 0]],
        "pauli_z": [[1, 0], [0, -1]],
        "phase_s": [[1, 0], [0, 1j]],
        "t_gate": [[1, 0], [0, cmath.exp(1j * math.pi / 4)]],
    }
    states = {"0": [1, 0], "1": [0, 1], "+": [1 / math.sqrt(2), 1 / math.sqrt(2)], "-": [1 / math.sqrt(2), -1 / math.sqrt(2)]}
    state = states.get(initial_state, states["0"])
    gate = gates.get(operation)
    if gate is None:
        return f"Unknown gate: {operation}. Available: {list(gates.keys())}"
    new_state = [gate[0][0] * state[0] + gate[0][1] * state[1], gate[1][0] * state[0] + gate[1][1] * state[1]]
    probs = [abs(a) ** 2 for a in new_state]

    def fmt(c):
        if isinstance(c, complex):
            if c.imag == 0:
                return f"{c.real:.4f}"
            return f"{c.real:.4f}{c.imag:+.4f}i"
        return f"{c:.4f}"

    return (f"Quantum simulation: {operation} on |{initial_state}>\n"
            f"Input state:  [{fmt(state[0])}, {fmt(state[1])}]\n"
            f"Output state: [{fmt(new_state[0])}, {fmt(new_state[1])}]\n"
            f"P(|0>) = {probs[0]:.4f}, P(|1>) = {probs[1]:.4f}")


# --- 13. invention_patent ---
def _invention_patent(args: dict, ctx):
    title = args.get("title", "Novel Invention")
    field = args.get("field", "technology")
    description = args.get("description", "A novel method and apparatus")
    claims_count = args.get("claims_count", 5)
    patent = {
        "document_type": "Provisional Patent Application",
        "title": title,
        "field_of_invention": field,
        "abstract": f"The present invention relates to {field}. {description}. The invention provides improved performance, efficiency, and user experience over existing solutions.",
        "background": f"The field of {field} has seen significant advancement. However, existing solutions suffer from [limitation 1], [limitation 2], and [limitation 3]. There is a need for [improvement].",
        "summary": f"{description}. The invention addresses the above limitations by providing [key innovation]. In one embodiment, [primary mechanism]. In another embodiment, [secondary mechanism].",
        "claims": [f"Claim {i + 1}: {'An apparatus' if i == 0 else 'The apparatus of claim 1, further'} comprising [component/method step {i + 1}]" for i in range(claims_count)],
        "drawings_needed": ["Fig. 1 - System overview", "Fig. 2 - Component diagram", "Fig. 3 - Flow chart", "Fig. 4 - Detailed view"],
        "prior_art_search": {"databases": ["Google Patents", "USPTO", "EPO Espacenet"], "keywords": [field, title.lower()]},
    }
    return f"Provisional patent draft for '{title}':\n```json\n{_j(patent)}\n```"


# --- 14. research_paper ---
def _research_paper(args: dict, ctx):
    topic = args.get("topic", "Machine Learning")
    paper_type = args.get("paper_type", "conference")
    sections = args.get("sections", None)
    templates = {
        "conference": {"format": "IEEE/ACM", "page_limit": "8-10 pages", "sections": ["Abstract (250 words)", "Introduction", "Related Work", "Methodology", "Experiments", "Results & Discussion", "Conclusion", "References"]},
        "journal": {"format": "Elsevier/Springer", "page_limit": "15-25 pages", "sections": ["Abstract (300 words)", "Introduction", "Literature Review", "Theoretical Framework", "Methodology", "Experimental Setup", "Results", "Discussion", "Limitations & Future Work", "Conclusion", "References", "Appendix"]},
        "arxiv": {"format": "LaTeX (arxiv style)", "page_limit": "no limit", "sections": ["Abstract", "Introduction", "Background", "Method", "Experiments", "Results", "Conclusion", "References"]},
        "workshop": {"format": "Extended Abstract", "page_limit": "4 pages", "sections": ["Abstract (150 words)", "Introduction & Motivation", "Approach", "Preliminary Results", "Discussion", "References"]},
    }
    tmpl = templates.get(paper_type, templates["conference"])
    if sections:
        tmpl["sections"] = sections
    outline = {
        "topic": topic, "type": paper_type, **tmpl,
        "writing_tips": ["Start with methodology, then results", "Write intro and abstract last", "Each section should have a clear topic sentence", "Use active voice for clarity"],
        "latex_template": "\\documentclass{article}\n\\title{" + topic + "}\n\\begin{document}\n\\maketitle\n\\end{document}",
    }
    return f"Research paper outline for '{topic}' ({paper_type}):\n```json\n{_j(outline)}\n```"


# --- 15. experiment_designer ---
def _experiment_designer(args: dict, ctx):
    hypothesis = args.get("hypothesis", "Treatment X improves outcome Y")
    field = args.get("field", "computer_science")
    design_type = args.get("design_type", "controlled")
    experiment = {
        "hypothesis": hypothesis,
        "field": field,
        "design": {
            "type": design_type,
            "independent_variables": ["[Variable to manipulate]"],
            "dependent_variables": ["[Variable to measure]"],
            "control_variables": ["[Variables to keep constant]"],
            "control_group": "Baseline without treatment",
            "sample_size": {"recommendation": "Use power analysis", "alpha": 0.05, "power": 0.80, "effect_size": "medium"},
        },
        "methodology": {
            "randomization": True,
            "blinding": "double-blind" if field in ["medicine", "psychology"] else "single-blind",
            "replication": 3,
            "data_collection": ["pre-test", "treatment", "post-test", "follow-up"],
        },
        "statistical_analysis": {
            "primary_test": {"controlled": "t-test / ANOVA", "correlational": "Pearson/Spearman", "observational": "regression analysis"}.get(design_type, "t-test"),
            "assumptions_to_check": ["normality (Shapiro-Wilk)", "homogeneity of variance (Levene's)", "independence"],
            "effect_size": "Cohen's d / eta-squared",
            "corrections": "Bonferroni for multiple comparisons",
        },
        "ethical_considerations": ["IRB approval if human subjects", "Informed consent", "Data privacy", "Conflict of interest disclosure"],
    }
    return f"Experiment design for '{hypothesis}':\n```json\n{_j(experiment)}\n```"


def get_tools():
    return [
        ToolEntry(name="train_model_config", description="Generate training configs for ML models (lr, batch size, epochs, optimizer)", parameters={"type": "object", "properties": {"model_type": {"type": "string", "enum": ["classification", "regression", "nlp", "vision"]}, "framework": {"type": "string"}, "dataset_size": {"type": "integer"}}, "required": []}, handler=_train_model_config),
        ToolEntry(name="dataset_prep", description="Generate data preprocessing pipelines with cleaning, normalization, augmentation, splitting", parameters={"type": "object", "properties": {"data_type": {"type": "string", "enum": ["tabular", "text", "image", "audio"]}, "task": {"type": "string"}, "split_ratio": {"type": "string"}}, "required": []}, handler=_dataset_prep),
        ToolEntry(name="model_architecture", description="Design neural network architectures (CNN, RNN, Transformer, GAN, VAE, Diffusion)", parameters={"type": "object", "properties": {"architecture": {"type": "string", "enum": ["cnn", "rnn", "transformer", "gan", "vae", "diffusion"]}, "input_shape": {"type": "string"}, "num_classes": {"type": "integer"}}, "required": []}, handler=_model_architecture),
        ToolEntry(name="hyperparameter_search", description="Generate hyperparameter search configs (grid, random, Bayesian)", parameters={"type": "object", "properties": {"method": {"type": "string", "enum": ["grid", "random", "bayesian"]}, "model_type": {"type": "string"}, "budget": {"type": "integer"}}, "required": []}, handler=_hyperparameter_search),
        ToolEntry(name="llm_fine_tune", description="Generate LLM fine-tuning configs (LoRA, QLoRA, full) with dataset templates", parameters={"type": "object", "properties": {"method": {"type": "string", "enum": ["lora", "qlora", "full"]}, "base_model": {"type": "string"}, "dataset_format": {"type": "string", "enum": ["alpaca", "sharegpt", "jsonl"]}}, "required": []}, handler=_llm_fine_tune),
        ToolEntry(name="llm_prompt_engineer", description="Craft system prompts, few-shot examples, chain-of-thought, tool-use prompts", parameters={"type": "object", "properties": {"style": {"type": "string", "enum": ["system", "few_shot", "chain_of_thought", "tool_use", "react"]}, "task": {"type": "string"}}, "required": []}, handler=_llm_prompt_engineer),
        ToolEntry(name="eval_framework", description="Generate model evaluation scripts with metrics (accuracy, F1, BLEU, perplexity)", parameters={"type": "object", "properties": {"task": {"type": "string", "enum": ["classification", "regression", "nlp_generation", "language_model", "object_detection", "ranking"]}}, "required": []}, handler=_eval_framework),
        ToolEntry(name="rag_pipeline", description="Design RAG pipelines with chunking, embedding, retrieval, reranking", parameters={"type": "object", "properties": {"doc_type": {"type": "string", "enum": ["pdf", "html", "markdown", "code"]}, "embedding_model": {"type": "string"}, "retriever": {"type": "string", "enum": ["vector", "hybrid", "bm25"]}}, "required": []}, handler=_rag_pipeline),
        ToolEntry(name="model_deploy", description="Generate deployment configs (FastAPI, vLLM, TGI, ONNX, quantization)", parameters={"type": "object", "properties": {"method": {"type": "string", "enum": ["fastapi", "vllm", "tgi", "onnx"]}, "model_type": {"type": "string"}, "quantization": {"type": "string", "enum": ["gptq", "awq", "gguf"]}}, "required": []}, handler=_model_deploy),
        ToolEntry(name="training_monitor", description="Generate training dashboard configs (loss curves, gradient norms, LR schedule)", parameters={"type": "object", "properties": {"backend": {"type": "string", "enum": ["wandb", "tensorboard", "mlflow"]}, "metrics": {"type": "array", "items": {"type": "string"}}}, "required": []}, handler=_training_monitor),
        ToolEntry(name="quantum_circuit", description="Generate quantum circuit descriptions for algorithms (Grover, Shor, VQE, QAOA)", parameters={"type": "object", "properties": {"algorithm": {"type": "string", "enum": ["grover", "shor", "vqe", "qaoa"]}, "n_qubits": {"type": "integer"}}, "required": []}, handler=_quantum_circuit),
        ToolEntry(name="quantum_simulation", description="Simulate quantum states and gate operations using pure Python", parameters={"type": "object", "properties": {"operation": {"type": "string", "enum": ["hadamard", "pauli_x", "pauli_z", "phase_s", "t_gate"]}, "initial_state": {"type": "string", "enum": ["0", "1", "+", "-"]}}, "required": []}, handler=_quantum_simulation),
        ToolEntry(name="invention_patent", description="Generate provisional patent application drafts", parameters={"type": "object", "properties": {"title": {"type": "string"}, "field": {"type": "string"}, "description": {"type": "string"}, "claims_count": {"type": "integer"}}, "required": ["title"]}, handler=_invention_patent),
        ToolEntry(name="research_paper", description="Generate research paper outlines with sections and LaTeX template", parameters={"type": "object", "properties": {"topic": {"type": "string"}, "paper_type": {"type": "string", "enum": ["conference", "journal", "arxiv", "workshop"]}, "sections": {"type": "array", "items": {"type": "string"}}}, "required": ["topic"]}, handler=_research_paper),
        ToolEntry(name="experiment_designer", description="Design scientific experiments with hypothesis, variables, controls, stats plan", parameters={"type": "object", "properties": {"hypothesis": {"type": "string"}, "field": {"type": "string"}, "design_type": {"type": "string", "enum": ["controlled", "correlational", "observational"]}}, "required": ["hypothesis"]}, handler=_experiment_designer),
    ]
