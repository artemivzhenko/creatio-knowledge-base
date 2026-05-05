using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

/// <summary>
/// Pattern: serialize a Creatio Entity to JSON (JObject) for integration payloads,
/// audit logs, or API responses — without manually enumerating every column.
///
/// Features:
///   - Iterates all schema columns automatically
///   - Lookup columns serialize as { "Id": "...", "DisplayValue": "..." }
///   - Regular columns serialize as their raw value
///   - Configurable ignored-column list (system columns, large blobs, etc.)
///   - Optional column whitelist — serialize only what you need
///   - Optional detail serialization — include related detail records as a JSON array
/// </summary>
namespace Terrasoft.Configuration {

    public class EntitySerializer {

        private readonly UserConnection     _userConnection;
        private readonly HashSet<string>    _skipColumns;

        // Default system columns excluded unless overridden
        private static readonly string[] DefaultSkipColumns = {
            "ProcessListeners", "SysModifiedInSchemaUId", "SysCreatedInSchemaUId"
        };

        public EntitySerializer(UserConnection userConnection) {
            _userConnection = userConnection;
            _skipColumns = new HashSet<string>(DefaultSkipColumns);
        }

        // Add columns to the skip list (e.g. large binary columns, sensitive data)
        public void Ignore(params string[] columnNames) {
            foreach (var col in columnNames)
                _skipColumns.Add(col);
        }

        // Serialize all non-ignored columns of the entity
        public JObject Serialize(string schemaName, Guid recordId) {
            var entity = LoadEntity(schemaName, recordId);
            return entity != null ? BuildObject(entity, null) : null;
        }

        // Serialize only the specified columns (whitelist)
        public JObject Serialize(string schemaName, Guid recordId,
            IEnumerable<string> columnNames) {

            var entity = LoadEntity(schemaName, recordId, columnNames);
            return entity != null ? BuildObject(entity, new HashSet<string>(columnNames)) : null;
        }

        // Serialize entity + related detail records as a nested array
        // detailColumns: key = detail schema name, value = FK column linking detail to parent
        public JObject SerializeWithDetails(string schemaName, Guid recordId,
            Dictionary<string, string> detailColumns) {

            JObject root = Serialize(schemaName, recordId);
            if (root == null) return null;

            foreach (var kv in detailColumns) {
                string detailSchema    = kv.Key;
                string fkColumnName    = kv.Value;

                var detailEsq = new EntitySchemaQuery(
                    _userConnection.EntitySchemaManager, detailSchema);
                detailEsq.AddAllSchemaColumns();
                detailEsq.PrimaryQueryColumn.IsAlwaysSelect = true;
                detailEsq.Filters.Add(detailEsq.CreateFilterWithParameters(
                    FilterComparisonType.Equal, fkColumnName, recordId));

                var detailArray = new JArray();
                foreach (var detailEntity in detailEsq.GetEntityCollection(_userConnection))
                    detailArray.Add(BuildObject(detailEntity, null));

                root[detailSchema] = detailArray;
            }

            return root;
        }

        // ── Internal ──────────────────────────────────────────────────────────

        private Entity LoadEntity(string schemaName, Guid recordId,
            IEnumerable<string> columns = null) {

            var esq = new EntitySchemaQuery(_userConnection.EntitySchemaManager, schemaName);
            esq.PrimaryQueryColumn.IsAlwaysSelect = true;

            if (columns != null) {
                foreach (var col in columns)
                    esq.AddColumn(col);
            }
            else {
                esq.AddAllSchemaColumns();
            }

            return esq.GetEntity(_userConnection, recordId);
        }

        private JObject BuildObject(Entity entity, HashSet<string> whitelist) {
            var obj = new JObject();

            foreach (EntitySchemaColumn column in entity.Schema.Columns) {
                if (_skipColumns.Contains(column.Name)) continue;
                if (whitelist != null && !whitelist.Contains(column.Name)) continue;

                if (column.IsLookupType) {
                    // Lookup: serialize as { "Id": "...", "DisplayValue": "..." }
                    var idValue = entity.GetColumnValue(column.Name + "Id");
                    var displayValue = entity.GetColumnValue(column.Name);
                    obj[column.Name] = new JObject {
                        ["Id"]           = idValue != null ? new JValue(idValue) : JValue.CreateNull(),
                        ["DisplayValue"] = displayValue != null
                            ? new JValue(displayValue.ToString())
                            : JValue.CreateNull()
                    };
                }
                else {
                    var value = entity.GetColumnValue(column.Name);
                    obj[column.Name] = value != null
                        ? new JValue(value)
                        : JValue.CreateNull();
                }
            }

            return obj;
        }
    }
}
