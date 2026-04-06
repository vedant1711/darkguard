import re

# 1. Update README.md
with open('README.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('four independent AI/rules-based analyzers', 'ten independent AI/rules-based analyzers')
text = text.replace('four standalone analyzers concurrently', 'ten standalone analyzers concurrently')
text = text.replace('four independent analyzers', 'ten independent analyzers')

old_table = """| **Review** | Review text blobs | Heuristics + LLM | Fake Social Proof |"""
new_table = """| **Review** | Review text blobs | Heuristics + LLM | Fake Social Proof |
| **Consent** | Pre-checked consent / choice architecture | Rules engine | Asymmetric choice, prechecked consent |
| **Checkout Flow** | Pricing changes / extra items | Rules engine | Basket sneaking, drip pricing |
| **Subscription** | Continuity terms | LLM | Roach motel, forced continuity |
| **Privacy** | Default sharing settings | Rules engine | Privacy Zuckering |
| **Nagging** | Repeated prompts / overlays | Rules engine | Notification inflation, persistent nagging |
| **Pricing** | Multi-tier pricing / BNPL options | LLM | Price anchoring, BNPL deception |"""
text = text.replace(old_table, new_table)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(text)

# 2. Update docs/architecture.md
with open('docs/architecture.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('4 analyzers', '10 analyzers')
text = text.replace('four analyzers', 'ten analyzers')
old_analyzers = """        DOM["DOM Analyzer<br/><i>Rules Engine</i>"]
        TXT["Text Analyzer<br/><i>Regex + NLP</i>"]
        VIS["Visual Analyzer<br/><i>ElementMap → LLM</i>"]
        REV["Review Analyzer<br/><i>Heuristics + LLM</i>"]"""
new_analyzers = """        DOM["DOM Analyzer<br/><i>Rules Engine</i>"]
        TXT["Text Analyzer<br/><i>Regex + NLP</i>"]
        VIS["Visual Analyzer<br/><i>ElementMap → LLM</i>"]
        REV["Review Analyzer<br/><i>Heuristics + LLM</i>"]
        CON["Consent Analyzer<br/><i>Rules</i>"]
        CHK["Checkout Analyzer<br/><i>Rules</i>"]
        SUB["Subscription Analyzer<br/><i>LLM</i>"]
        PRV["Privacy Analyzer<br/><i>Rules</i>"]
        NAG["Nagging Analyzer<br/><i>Rules</i>"]
        PRC["Pricing Analyzer<br/><i>LLM</i>"]"""
text = text.replace(old_analyzers, new_analyzers)

text = text.replace('DISP -->|"asyncio.wait_for(10s)"| REV', 'DISP -->|"asyncio.wait_for(10s)"| REV\\n    DISP -->|"asyncio.wait_for(10s)"| CON\\n    DISP -->|"asyncio.wait_for(10s)"| CHK\\n    DISP -->|"asyncio.wait_for(10s)"| SUB\\n    DISP -->|"asyncio.wait_for(10s)"| PRV\\n    DISP -->|"asyncio.wait_for(10s)"| NAG\\n    DISP -->|"asyncio.wait_for(10s)"| PRC')

old_apps = """        DA["dom_analyzer/<br/>service.py"]
        TA["text_analyzer/<br/>service.py"]
        VA["visual_analyzer/<br/>service.py<br/>element_map_builder.py"]
        RA["review_analyzer/<br/>service.py"]"""
new_apps = old_apps + """
        CA["consent_analyzer/<br/>service.py"]
        CFA["checkout_flow_analyzer/<br/>service.py"]
        SA["subscription_analyzer/<br/>service.py"]
        PA["privacy_analyzer/<br/>service.py"]
        NA["nagging_analyzer/<br/>service.py"]
        PRA["pricing_analyzer/<br/>service.py"]"""
text = text.replace(old_apps, new_apps)

with open('docs/architecture.md', 'w', encoding='utf-8') as f:
    f.write(text)

# 3. Update docs/data-flow.md
with open('docs/data-flow.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('4 analyzers run in parallel', '10 analyzers run in parallel')
text = text.replace('Fan-out to 4 analyzers', 'Fan-out to 10 analyzers')
text = text.replace('D5["Review text<br/>(review containers)"]', 'D5["Review text<br/>(review containers)"]\\n    D --> D6["Checkout flow<br/>(pricing, cart)"]\\n    D --> D7["Nagging events<br/>(overlays, toasts)"]')
text = text.replace('D4 & D5', 'D4 & D5 & D6 & D7')

old_fork = """    FORK --> DOM["DomAnalyzerService.analyze()"]
    FORK --> TXT["TextAnalyzerService.analyze()"]
    FORK --> VIS["VisualAnalyzerService.analyze()"]
    FORK --> REV["ReviewAnalyzerService.analyze()"]"""
new_fork = old_fork + """
    FORK --> CON["ConsentAnalyzerService.analyze()"]
    FORK --> CHK["CheckoutFlowAnalyzerService.analyze()"]
    FORK --> SUB["SubscriptionAnalyzerService.analyze()"]
    FORK --> PRV["PrivacyAnalyzerService.analyze()"]
    FORK --> NAG["NaggingAnalyzerService.analyze()"]
    FORK --> PRC["PricingAnalyzerService.analyze()"]"""
text = text.replace(old_fork, new_fork)

text = text.replace('DOM_R & TXT_R & VIS_R & REV_R --> MERGE["Merge all detections"]', 'DOM_R & TXT_R & VIS_R & REV_R & CON_R & CHK_R & SUB_R & PRV_R & NAG_R & PRC_R --> MERGE["Merge all detections"]')
text = text.replace('DOM --> DOM_R', 'DOM --> DOM_R\\n    CON --> CON_R\\n    CHK --> CHK_R\\n    SUB --> SUB_R\\n    PRV --> PRV_R\\n    NAG --> NAG_R\\n    PRC --> PRC_R')

with open('docs/data-flow.md', 'w', encoding='utf-8') as f:
    f.write(text)

# 4. Update docs/api.md
with open('docs/api.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('Run all four dark-pattern analyzers', 'Run all ten dark-pattern analyzers')

old_endpoints = """## `POST /api/analyze`"""
new_endpoints = """## Endpoints Overview

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/analyze` | Run all analyzers. Returns `detections[]`, `audit_report`, `scan_id` |
| `POST` | `/api/scans/crawl` | Server-side Playwright crawl + full analysis pipeline |
| `GET` | `/api/scans/` | Paginated scan history |
| `GET` | `/api/scans/<id>/` | Single scan with all detection records |
| `GET` | `/api/scans/<id>/report/` | Full compliance audit report (JSON) |
| `GET` | `/api/scans/<id>/report/pdf` | Styled HTML compliance report (print-to-PDF) |

## `POST /api/analyze`"""
text = text.replace(old_endpoints, new_endpoints)

old_categories = """One of: `preselection`, `visual_interference`, `confirmshaming`, `urgency_scarcity`, `misdirection`, `fake_social_proof`, `hidden_costs`"""
new_categories = """19 categories including: `preselection`, `visual_interference`, `confirmshaming`, `urgency_scarcity`, `misdirection`, `fake_social_proof`, `hidden_costs`, `asymmetric_choice`, `prechecked_consent`, `basket_sneaking`, `drip_pricing`, `roach_motel`, `forced_continuity`, `plan_comparison_trick`, `privacy_zuckering`, `notification_inflation`, `persistent_nagging`, `price_anchoring`, `bnpl_deception`, `intermediate_currency`"""
text = text.replace(old_categories, new_categories)

with open('docs/api.md', 'w', encoding='utf-8') as f:
    f.write(text)

# 5. Update docs/analyzers.md
with open('docs/analyzers.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('four dark-pattern analyzers', 'ten dark-pattern analyzers')
text = text.replace('**7 categories**', '**19 categories**')
text = text.replace('four independent analyzers', 'ten independent analyzers')

with open('docs/analyzers.md', 'w', encoding='utf-8') as f:
    f.write(text)
