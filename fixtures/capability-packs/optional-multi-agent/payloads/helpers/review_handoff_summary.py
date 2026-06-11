def summarize_handoff(scope, verification, residual_risks):
    return {
        "scope": list(scope),
        "verification": list(verification),
        "residual_risks": list(residual_risks),
    }
