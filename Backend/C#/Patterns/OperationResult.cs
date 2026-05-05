using System;
using System.Collections.Generic;

/// <summary>
/// Pattern: typed operation result — a lightweight alternative to throwing exceptions
/// for expected failures in service/feature methods.
///
/// Use OperationResult&lt;T&gt; when:
///   - a method can fail for a known, business-level reason (not a bug);
///   - the caller must decide what to do on failure (retry, show message, skip);
///   - you want a single return type that carries both the outcome and the data.
///
/// Use OperationResult (non-generic) for operations that return no data (void-like).
///
/// Factory methods enforce consistent construction:
///   OperationResult&lt;Guid&gt;.Ok(newId)
///   OperationResult&lt;Guid&gt;.Fail("Record already exists")
///   OperationResult.Ok()
///   OperationResult.Fail("Validation failed")
/// </summary>
namespace Terrasoft.Configuration {

    // ── Generic variant — operation with a result value ───────────────────────

    public class OperationResult<T> {

        public bool   IsSuccess { get; private set; }
        public T      Data      { get; private set; }
        public string Error     { get; private set; }

        private OperationResult() { }

        public static OperationResult<T> Ok(T data) {
            return new OperationResult<T> { IsSuccess = true, Data = data };
        }

        public static OperationResult<T> Fail(string error) {
            return new OperationResult<T> { IsSuccess = false, Error = error };
        }

        // Map data to a different type — only executes the transform on success
        public OperationResult<TOut> Map<TOut>(Func<T, TOut> transform) {
            return IsSuccess
                ? OperationResult<TOut>.Ok(transform(Data))
                : OperationResult<TOut>.Fail(Error);
        }

        public override string ToString() {
            return IsSuccess
                ? string.Format("Ok({0})", Data)
                : string.Format("Fail({0})", Error);
        }
    }

    // ── Non-generic variant — operation that returns no value ─────────────────

    public class OperationResult {

        public bool   IsSuccess { get; private set; }
        public string Error     { get; private set; }

        private OperationResult() { }

        public static OperationResult Ok() {
            return new OperationResult { IsSuccess = true };
        }

        public static OperationResult Fail(string error) {
            return new OperationResult { IsSuccess = false, Error = error };
        }

        public override string ToString() {
            return IsSuccess ? "Ok" : string.Format("Fail({0})", Error);
        }
    }

    // ── Bulk variant — tracks per-item outcomes ───────────────────────────────

    public class BulkOperationResult {

        private readonly List<string> _errors = new List<string>();

        public int SuccessCount { get; private set; }
        public int ErrorCount   { get; private set; }
        public IReadOnlyList<string> Errors => _errors.AsReadOnly();

        public bool IsFullSuccess   => ErrorCount == 0 && SuccessCount > 0;
        public bool IsPartialSuccess => SuccessCount > 0 && ErrorCount > 0;
        public bool IsFullFailure    => SuccessCount == 0;

        public void RecordSuccess() {
            SuccessCount++;
        }

        public void RecordFailure(string error) {
            ErrorCount++;
            _errors.Add(error);
        }

        public string Summary {
            get {
                return string.Format("{0} succeeded, {1} failed", SuccessCount, ErrorCount);
            }
        }
    }
}
