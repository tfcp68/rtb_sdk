# Forecasting comparison

[All benchmark results](../README.md)

The [predictor benchmark report](predictor_benchmark_report.md) compares the SDK's
Prophet implementation with statistical, neural and tree-based alternatives
using rolling-origin evaluation across several series and forecast horizons.
It reports forecast accuracy, uncertainty across origins and fitting time.

In the saved aggregate ranking, pmdarima AutoARIMA has mean accuracy 0.9119,
compared with 0.8275 for the Prophet baseline (`accuracy = 1 - MAPE`). This is an
experimental aggregate, not a promise for every series: winners vary by data,
horizon and fitting cost. The report also records the monthly-frequency
conversion bug found during evaluation and distinguishes the corrected results.

[Predictor improvements](predictor_improvements.md) discusses implementation
options and follow-up work. Alternative models in the experiment are not all
integrated into the SDK. Source datasets are local inputs and are not included.
