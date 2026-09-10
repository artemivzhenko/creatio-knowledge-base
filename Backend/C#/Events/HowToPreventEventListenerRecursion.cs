using System;
using Common.Logging;
using Terrasoft.Common;
using Terrasoft.Core;
using Terrasoft.Core.Entities;
using Terrasoft.Core.Entities.Events;

/// <summary>
/// Demonstrates how to stop an entity event listener from re-entering itself.
///
/// THE PROBLEM. An event listener that writes to the entity it listens to — or to another
/// entity whose listener writes back — re-triggers itself. The symptoms are a stack overflow,
/// a hung save, or duplicated side effects such as an approval created twice.
/// It is easy to miss in testing because it only shows up once a second listener is added.
///
/// THE GUARD. A static flag marked [ThreadStatic] that the helper raises around its own
/// writes, and every listener checks before doing anything.
///
/// WHY [ThreadStatic] AND NOT A PLAIN static. Creatio serves many requests in parallel on
/// the same process. A plain static flag would be shared across all of them, so one user's
/// internal operation would silently suppress another user's legitimate event. [ThreadStatic]
/// gives each request thread its own copy.
///
/// ALWAYS RESET IN A finally. An exception thrown while the flag is raised would otherwise
/// leave the thread permanently "internal", and that thread would ignore every later event —
/// a bug that survives until the app pool recycles.
///
/// WHAT THIS DOES NOT COVER. The flag is per thread, so it does not protect work that has
/// been handed to a background task or a business process; those run on their own threads and
/// see the flag as false. For those, guard with a column on the record instead.
///
/// LIGHTER ALTERNATIVES, prefer them when they fit:
///   e.ModifiedColumnValues — react only when the columns you care about actually changed.
///   entity.SetColumnValue in a BEFORE event — changes the record in flight without a second
///   save, so no event is raised at all.
/// </summary>
namespace Terrasoft.Configuration
{

	public class CaseVisaHelper
	{

		private static readonly ILog _log = LogManager.GetLogger("UsrCaseVisa");

		// One copy per request thread.
		[ThreadStatic]
		private static bool _isInternalOperation;

		/// <summary>
		/// Listeners read this to tell "the user did it" from "we did it".
		/// </summary>
		public static bool IsInternalOperation {
			get { return _isInternalOperation; }
		}

		private readonly UserConnection _userConnection;

		public CaseVisaHelper(UserConnection userConnection) {
			userConnection.CheckArgumentNull("userConnection");
			_userConnection = userConnection;
		}

		/// <summary>
		/// Writes that must not be seen by our own listeners.
		/// </summary>
		public virtual void CreateApprovals(Guid caseId) {
			_isInternalOperation = true;
			try {
				// Every save inside this block raises events, and every listener of ours
				// returns early because the flag is set.
				var esq = new EntitySchemaQuery(_userConnection.EntitySchemaManager, "SysApproval");
				esq.AddColumn("Id");
				// ... create / update approval records here
			} finally {
				// Reset even when something throws.
				_isInternalOperation = false;
			}
		}

		/// <summary>
		/// The guard is also useful on the read path, to skip expensive recalculation
		/// while an internal operation is in flight.
		/// </summary>
		public virtual void RecalculateVisaState(Entity caseEntity) {
			if (_isInternalOperation || caseEntity == null) {
				return;
			}
			// ... recalculation
		}
	}

	/// <summary>
	/// The listener checks the flag first and does nothing during our own writes.
	/// </summary>
	[EntityEventListener(SchemaName = "SysApproval")]
	public class ApprovalEventListener : BaseEntityEventListener
	{

		private const string CaseSchemaName = "Case";

		public override void OnSaved(object sender, EntityAfterEventArgs e) {
			base.OnSaved(sender, e);

			// 1. Our own write - ignore it.
			if (CaseVisaHelper.IsInternalOperation) {
				return;
			}

			// 2. Standard defensive checks.
			var entity = sender as Entity;
			if (entity == null || entity.UserConnection == null) {
				return;
			}

			// 3. Only the records this listener is about.
			if (entity.GetTypedColumnValue<string>("ReferenceSchemaName") != CaseSchemaName) {
				return;
			}

			// 4. Only when a column we care about actually changed - this alone removes
			//    most of the redundant executions. Two equivalent forms:
			//       e.ModifiedColumnValues.FindByName("StatusId") != null
			//       e.ModifiedColumnValues.Any(cv => cv.Name == "StatusId")
			//    There is no Contains(string) overload on this collection.
			if (e == null || e.ModifiedColumnValues == null
				|| e.ModifiedColumnValues.FindByName("StatusId") == null) {
				return;
			}

			// ... react to the real, user-driven change
		}
	}
}
