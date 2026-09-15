using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Demonstrates UseAdminRights — the switch that decides whether a query or a save respects
/// record-level access rights, and the related Entity helpers for creating records.
///
/// THE DEFAULT IS NOT WHAT MOST PEOPLE EXPECT. EntitySchemaQuery and Entity default to
/// UseAdminRights = true, which BYPASSES record permissions. Code written without thinking
/// about it therefore reads and writes rows the current user is not allowed to see. Set it
/// to false whenever the operation acts on behalf of a user.
///
///   esq.UseAdminRights = false;      // query respects the user's rights
///   entity.UseAdminRights = false;   // save respects the user's rights
///
/// WHEN true IS CORRECT: a background job, a system integration, or a deliberate
/// elevation such as "any user may log an audit row". Make that intent explicit in a
/// comment - a reviewer cannot tell an intentional elevation from a forgotten default.
///
/// A related but different question is WHICH CONNECTION you run on:
///   UserConnection                 the caller, with their permissions
///   AppConnection.SystemUserConnection  the Supervisor context
/// UseAdminRights = false on a SystemUserConnection still runs as Supervisor - the flag
/// narrows to the connection's user, it does not switch users.
/// See HowToUseSystemUserConnection.
///
/// CREATING A RECORD WITH DEFAULTS:
///   SetDefColumnValues()  fills the columns that have default values configured on the
///                         object - lookup defaults, current date, current user, and the
///                         process/system columns. Without it a record created in code
///                         differs from one created through the UI.
///   Save(false)           saves WITHOUT raising entity events. Use it to avoid triggering
///                         listeners when you are already inside one; Save() (or Save(true))
///                         raises them normally. Skipping events also skips validation done
///                         in listeners, so do not use it as a shortcut around a rule you
///                         find inconvenient.
///
/// CREATING AN ENTITY BY SCHEMA NAME, when the entity is only known at runtime:
///   UserConnection.EntitySchemaManager.GetInstanceByName(name).CreateEntity(userConnection)
/// </summary>
namespace Terrasoft.Configuration
{

	public class UsrEntityHelper
	{

		protected UserConnection UserConnection;

		public UsrEntityHelper(UserConnection userConnection) {
			UserConnection = userConnection;
		}

		/// <summary>
		/// Creates a record of any entity, with platform defaults applied, under the rights
		/// of the current user.
		/// </summary>
		public Guid CreateDefaultRecord(string entitySchemaName) {
			var entity = UserConnection.EntitySchemaManager
				.GetInstanceByName(entitySchemaName)
				.CreateEntity(UserConnection);

			// Respect the caller's permissions.
			entity.UseAdminRights = false;

			// Apply the defaults configured on the object.
			entity.SetDefColumnValues();

			// false - do not raise entity events for this write.
			entity.Save(false);

			return entity.PrimaryColumnValue;
		}

		/// <summary>
		/// A read that must not show the user rows they cannot access.
		/// </summary>
		public Entity GetFileEntity(Guid fileId) {
			var esq = new EntitySchemaQuery(UserConnection.EntitySchemaManager, "UsrApplicationFile");

			// Always select the primary column, even when it is not added explicitly.
			esq.PrimaryQueryColumn.IsAlwaysSelect = true;

			// Without this line the query would ignore record permissions.
			esq.UseAdminRights = false;

			esq.AddColumn("Name");
			esq.AddColumn("UsrApplication");

			return esq.GetEntity(UserConnection, fileId);
		}

		/// <summary>
		/// A deliberate elevation. The comment is the point: it tells the next reader that
		/// the default was kept on purpose.
		/// </summary>
		public void WriteAuditRow(Guid recordId, string action) {
			var entity = UserConnection.EntitySchemaManager
				.GetInstanceByName("UsrAuditLog")
				.CreateEntity(UserConnection);

			// Elevated on purpose: every user may append to the audit log, even though
			// nobody has write access to it directly.
			entity.UseAdminRights = true;

			entity.SetDefColumnValues();
			entity.SetColumnValue("UsrRecordId", recordId);
			entity.SetColumnValue("UsrAction", action);
			entity.Save(false);
		}

		/// <summary>
		/// Updating an existing record under the caller's rights.
		/// </summary>
		public bool UpdateRecord(string entitySchemaName, Guid recordId, string columnName, object value) {
			var entity = UserConnection.EntitySchemaManager
				.GetInstanceByName(entitySchemaName)
				.CreateEntity(UserConnection);

			entity.UseAdminRights = false;

			// FetchFromDB returns false when the record does not exist OR the user may not
			// see it - the two cases are indistinguishable by design.
			if (!entity.FetchFromDB(recordId)) {
				return false;
			}

			entity.SetColumnValue(columnName, value);
			// Save() raises entity events; use it when listeners should react.
			entity.Save();
			return true;
		}
	}
}
