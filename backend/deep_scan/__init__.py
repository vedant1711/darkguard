# deep_scan — Multi-page workflow scanning engine.
# This is a service module, NOT an analyzer. It does not register with AnalyzerRegistry.
# Instead, it orchestrates Playwright to navigate through workflows and calls
# the standard dispatcher pipeline at each page.
