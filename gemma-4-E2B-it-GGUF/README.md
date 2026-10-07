# Modell-Ordner (kleineres Modell, optional)

Die eigentliche Modelldatei liegt **nicht** im Repo (siehe `.gitignore`). Optional
herunterladen, um im Tray-Menue unter "Sprachmodell" auf das kleinere und schnellere
Modell umschalten zu koennen:

```powershell
.\scripts\download_llm.ps1 -Modell E2B
```

Laedt `gemma-4-E2B-it-Q4_K_M.gguf` (ca. 3 GB) von
[unsloth/gemma-4-E2B-it-GGUF](https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF) direkt
in diesen Ordner.
