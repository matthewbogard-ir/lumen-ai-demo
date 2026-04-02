# Longines Demo — Predictable Flows

Six tested flows for reliable demo presentations. Each flow consistently triggers the correct product card or comparison modal.

## Single Product Flows

### Flow 1: HydroConquest (Flagship Diver)
**Prompt:** "Tell me about the HydroConquest"
**Expected result:** Longines HydroConquest 41mm — $1,700

### Flow 2: Moon Phase (Dress Watch)
**Prompt:** "I'm looking for a dress watch with a moon phase"
**Expected result:** The Longines Master Collection Moon Phase 40mm — $2,650

### Flow 4: DolceVita (Women's / Gift)
**Prompt:** "I want something elegant for my wife"
**Expected result:** Longines DolceVita 23.3 x 37mm — $1,200

### Flow 5: Chronograph
**Prompt:** "What's your best chronograph?"
**Expected result:** The Longines Master Collection Chronograph 40mm — $2,875

## Comparison Flows

### Flow 3: Spirit Flyback vs Spirit Zulu Time
**Prompt:** "Can you compare the Spirit Flyback and the Spirit Zulu Time?"
**Expected result:** Side-by-side comparison — Longines Spirit 40mm ($2,350) vs Longines Spirit Zulu Time 42mm ($2,875)

### Flow 6: HydroConquest vs HydroConquest GMT
**Prompt:** "Compare the HydroConquest and the HydroConquest GMT"
**Expected result:** Side-by-side comparison — Longines HydroConquest 41mm ($1,700) vs Longines HydroConquest GMT 41mm ($2,325)

## Tips

- Speak naturally — the avatar understands conversational language
- You don't need to close a product card before asking about another watch
- Filter console logs with `[WATCH-` prefix to debug matching issues
- After the demo session, trigger the lead summary email with:
  ```
  curl -X POST https://longines-session-monitor.purplebush-d6b18060.westus2.azurecontainerapps.io/process
  ```
