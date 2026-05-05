using System;
using System.Collections.Generic;
using global::Common.Logging;
using Terrasoft.Core;
using Terrasoft.Core.DB;
using Terrasoft.Core.Entities;

/// <summary>
/// Pattern: typed helper for a single entity schema.
/// Construct once with a schemaName and reuse across multiple operations —
/// avoids repeating ESQ setup, null-checks, and try/catch on every call site.
///
/// Methods split into two groups:
///   Entity-based (fires event handlers):  GetById, Save, Create, DeleteById
///   SQL-based (bypasses event handlers):  UpdateColumn, UpdateColumns
/// Choose based on whether OnSaving/OnSaved etc. must run for your operation.
/// </summary>
namespace Terrasoft.Configuration.AdditionalPatterns {

    public class ESQExtention {

        private readonly UserConnection _userConnection;
        private readonly EntitySchema   _schema;
        private readonly ILog           _log;

        public ESQExtention(UserConnection userConnection, string schemaName) {
            if (userConnection == null)
                throw new ArgumentNullException(nameof(userConnection));
            if (string.IsNullOrEmpty(schemaName))
                throw new ArgumentNullException(nameof(schemaName));

            _userConnection = userConnection;
            _schema = userConnection.EntitySchemaManager.GetInstanceByName(schemaName);
            _log    = LogManager.GetLogger("ESQExtention." + schemaName);
        }

        // ── Entity access ─────────────────────────────────────────────────────

        // Fetch by Id — throws if not found
        public Entity GetById(Guid id) {
            var entity = _schema.CreateEntity(_userConnection);
            if (!entity.FetchFromDB(id))
                throw new ESQExtentionException(
                    string.Format("Record not found in {0} with Id {1}", _schema.Name, id));
            return entity;
        }

        // Fetch by Id — returns null if not found (safe variant)
        public Entity TryGetById(Guid id) {
            var entity = _schema.CreateEntity(_userConnection);
            return entity.FetchFromDB(id) ? entity : null;
        }

        // Fetch by a single column value — returns null if not found
        public Entity TryGetByColumn(string columnName, object value) {
            var entity = _schema.CreateEntity(_userConnection);
            return entity.FetchFromDB(columnName, value) ? entity : null;
        }

        // Fetch only specific columns — cheaper than loading all when only a few values are needed
        public Entity GetWithColumns(Guid id, params string[] columnNames) {
            var esq = new EntitySchemaQuery(_userConnection.EntitySchemaManager, _schema.Name);
            esq.PrimaryQueryColumn.IsAlwaysSelect = true;
            foreach (var col in columnNames)
                esq.AddColumn(col);
            return esq.GetEntity(_userConnection, id);
        }

        // ── Single-value read ─────────────────────────────────────────────────

        // Read one column value for one record without loading the full entity
        public T GetColumnValue<T>(Guid id, string columnName) {
            var esq = new EntitySchemaQuery(_userConnection.EntitySchemaManager, _schema.Name);
            var col = esq.AddColumn(columnName);
            var entity = esq.GetEntity(_userConnection, id);
            if (entity == null)
                throw new ESQExtentionException(
                    string.Format("Record not found in {0} with Id {1}", _schema.Name, id));
            return entity.GetTypedColumnValue<T>(col.Name);
        }

        // ── Write (entity-based — fires event handlers) ───────────────────────

        // Create new record: SetDefColumnValues + set provided columns + Save
        // Returns the Id of the created record
        public Guid Create(Dictionary<string, object> columnValues) {
            var entity = _schema.CreateEntity(_userConnection);
            entity.SetDefColumnValues();
            if (columnValues != null) {
                foreach (var kv in columnValues)
                    entity.SetColumnValue(kv.Key, kv.Value);
            }
            if (!entity.Save())
                throw new ESQExtentionException(
                    string.Format("Failed to save new record in {0}", _schema.Name));
            return entity.PrimaryColumnValue;
        }

        // Save entity — wraps entity.Save() with try/catch and logging
        public bool Save(Entity entity) {
            try {
                return entity.Save();
            }
            catch (Exception ex) {
                _log.ErrorFormat("[ESQExtention.Save] {0} id={1}: {2}",
                    entity.SchemaName, entity.PrimaryColumnValue, ex.Message);
                return false;
            }
        }

        // Delete by Id — fires Deleting and Deleted event handlers
        public bool DeleteById(Guid id) {
            var entity = TryGetById(id);
            return entity != null && entity.Delete();
        }

        // ── Write (SQL-based — bypasses event handlers) ───────────────────────

        // Update a single column via SQL — faster, does NOT fire entity events
        public bool UpdateColumn(Guid id, string columnName, object value) {
            try {
                new Update(_userConnection, _schema.Name)
                    .Set(columnName, value != null ? Column.Parameter(value) : Column.Const(null))
                    .Where("Id").IsEqual(Column.Parameter(id))
                    .Execute();
                return true;
            }
            catch (Exception ex) {
                _log.ErrorFormat("[ESQExtention.UpdateColumn] {0} id={1} col={2}: {3}",
                    _schema.Name, id, columnName, ex.Message);
                return false;
            }
        }

        // Update multiple columns in one SQL statement — does NOT fire entity events
        public bool UpdateColumns(Guid id, Dictionary<string, object> columnValues) {
            try {
                // Anchor with 1=1 so .Set() calls can be added in a loop before the real WHERE
                var update = new Update(_userConnection, _schema.Name)
                    .Where(Column.Const(1)).IsEqual(Column.Const(1)) as Update;
                foreach (var kv in columnValues)
                    update = update.Set(kv.Key,
                        kv.Value != null ? Column.Parameter(kv.Value) : Column.Const(null));
                update.And("Id").IsEqual(Column.Parameter(id)).Execute();
                return true;
            }
            catch (Exception ex) {
                _log.ErrorFormat("[ESQExtention.UpdateColumns] {0} id={1}: {2}",
                    _schema.Name, id, ex.Message);
                return false;
            }
        }

        // ── Collection ────────────────────────────────────────────────────────

        // Get all records matching a simple column filter
        public EntityCollection GetByFilter(string columnName, object value) {
            var esq = new EntitySchemaQuery(_userConnection.EntitySchemaManager, _schema.Name);
            esq.AddAllSchemaColumns();
            esq.PrimaryQueryColumn.IsAlwaysSelect = true;
            esq.Filters.Add(
                esq.CreateFilterWithParameters(FilterComparisonType.Equal, columnName, value));
            return esq.GetEntityCollection(_userConnection);
        }

        // Iterate ALL records in batches — prevents memory overflow on large tables
        public void ForEach(Action<Entity> action, int batchSize = 5000) {
            var esq = new EntitySchemaQuery(_userConnection.EntitySchemaManager, _schema.Name);
            esq.AddAllSchemaColumns();
            esq.PrimaryQueryColumn.IsAlwaysSelect = true;
            ForEach(esq, action, batchSize);
        }

        // Iterate a pre-configured ESQ in batches — apply your own filters/columns first
        public void ForEach(EntitySchemaQuery esq, Action<Entity> action, int batchSize = 5000) {
            var options = new EntitySchemaQueryOptions {
                PageableDirection       = PageableSelectDirection.First,
                PageableConditionValues = new Dictionary<string, object>(),
                PageableRowCount        = batchSize,
                RowsOffset              = 0
            };
            EntityCollection batch;
            do {
                batch = esq.GetEntityCollection(_userConnection, options);
                foreach (var entity in batch)
                    action(entity);
                options.PageableDirection = PageableSelectDirection.Next;
                options.RowsOffset += batch.Count;
                esq.ResetSelectQuery();
            } while (batch.Count == batchSize);
        }
    }

    public class ESQExtentionException : Exception {
        public ESQExtentionException(string message) : base(message) { }
    }
}
