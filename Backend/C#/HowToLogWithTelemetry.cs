using System;
using global::Common.Logging;

/// <summary>
/// Demonstrates how to log messages in Creatio backend logic using Common.Logging.
/// Requires the "Telemetry Log" Marketplace app — after installation a log viewer appears
/// under Advanced Settings → Configuration.
/// Works in both cloud and on-site environments; logs are stored on the application server.
/// Use Info for normal flow, Warn for unexpected-but-recoverable states,
/// Error for caught exceptions, Debug for detailed diagnostic output (disabled in production).
/// </summary>
class HowToLogWithTelemetry {

    // Declare the logger as a field — one per class, named to match its owner
    private readonly ILog _log = LogManager.GetLogger("MyServiceLogger");

    public void DoWork(string input) {
        _log.InfoFormat("[DoWork] Started. input={0}", input);

        try {
            // custom logic

            _log.DebugFormat("[DoWork] Intermediate step completed. value={0}", input);
            _log.InfoFormat("[DoWork] Finished successfully.");
        }
        catch (Exception ex) {
            // Log the full exception message; use ex.ToString() for stack trace
            _log.ErrorFormat("[DoWork] Failed. Error={0}", ex.Message);
            throw;
        }
    }

    public void CheckState(string value) {
        if (string.IsNullOrEmpty(value)) {
            _log.WarnFormat("[CheckState] Value is empty — falling back to default.");
        }
    }
}
