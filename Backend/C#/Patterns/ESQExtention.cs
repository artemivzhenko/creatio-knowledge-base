using System;
using Terrasoft.Core;
using Terrasoft.Core.Entities;

namespace Terrasoft.Configuration.AdditionalPatterns {
    class ESQExtention
    {   
        private UserConnection uc;

        private IManager schema;
        public ESQExtention(UserConnection userConnection, string schemaName)
        {
            uc = userConnection;
            schema = uc.EntitySchemaManager.GetInstanceByName(schemaName);
        }

        public Entity GetEntityById(Guid recordId)
        {
            var entity = schema.CreateEntity(this.uc);
            if(!entity.FetchFromDB(recordId))
            {
                throw new ESQExtentionExceptions("Record by id not found");
            }
            return entity;
        }
    }

    class ESQExtentionExceptions : Exception
    {
        public ESQExtentionExceptions(string message)
            : base(message) { }

    }
}