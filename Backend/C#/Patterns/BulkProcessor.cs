using System;
using System.Collections.Generic;
using global::Common.Logging;
using Terrasoft.Core;

/// <summary>
/// Pattern: abstract base for bulk operations over a collection of items.
///
/// Inherit from BulkProcessor&lt;T&gt; and implement ProcessItem() with your domain logic.
/// The base handles:
///   - try/catch per item so one failure does not abort the whole batch;
///   - success/failure counting via BulkOperationResult;
///   - consistent logging with item identity.
///
/// Usage:
///   class CaseStatusUpdater : BulkProcessor&lt;Guid&gt; {
///       public CaseStatusUpdater(UserConnection uc) : base(uc) { }
///       protected override void ProcessItem(Guid caseId) {
///           // update one case
///       }
///   }
///   var result = new CaseStatusUpdater(uc).Run(caseIds);
/// </summary>
namespace Terrasoft.Configuration {

    public abstract class BulkProcessor<T> {

        protected readonly UserConnection _userConnection;
        protected readonly ILog           _log;

        protected BulkProcessor(UserConnection userConnection) {
            _userConnection = userConnection;
            _log = LogManager.GetLogger(GetType().Name);
        }

        // Execute the operation for every item; collects errors without aborting early
        public BulkOperationResult Run(IEnumerable<T> items) {
            var result = new BulkOperationResult();

            foreach (var item in items) {
                try {
                    ProcessItem(item);
                    result.RecordSuccess();
                }
                catch (Exception ex) {
                    string identity = GetItemIdentity(item);
                    _log.ErrorFormat("[{0}] Failed for {1}: {2}",
                        GetType().Name, identity, ex.Message);
                    result.RecordFailure(
                        string.Format("{0}: {1}", identity, ex.Message));
                }
            }

            _log.InfoFormat("[{0}] Completed. {1}", GetType().Name, result.Summary);
            return result;
        }

        // Implement the operation for a single item — called once per item in the collection
        protected abstract void ProcessItem(T item);

        // Override to improve log readability — default uses ToString()
        protected virtual string GetItemIdentity(T item) {
            return item != null ? item.ToString() : "null";
        }
    }

    // ── Concrete example — update a column for each record Id ────────────────

    // Shows BulkProcessor<Guid> in use without any additional infrastructure
    public class BulkColumnUpdater : BulkProcessor<Guid> {

        private readonly string _schemaName;
        private readonly string _columnName;
        private readonly object _newValue;

        public BulkColumnUpdater(UserConnection userConnection,
            string schemaName, string columnName, object newValue)
            : base(userConnection) {

            _schemaName = schemaName;
            _columnName = columnName;
            _newValue   = newValue;
        }

        protected override void ProcessItem(Guid recordId) {
            var helper = new ESQExtention(_userConnection, _schemaName);
            helper.UpdateColumn(recordId, _columnName, _newValue);
        }

        protected override string GetItemIdentity(Guid item) {
            return item.ToString();
        }
    }
}
