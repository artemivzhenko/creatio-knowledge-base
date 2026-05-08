using System;
using System.ServiceModel;
using System.ServiceModel.Activation;
using System.ServiceModel.Web;
using Terrasoft.Core;
using Terrasoft.Core.Entities;
using Terrasoft.Web.Common;

/// <summary>
/// Pattern: minimal Creatio custom web service.
///
/// Inherit from BaseService — it exposes UserConnection without any constructor work.
/// Decorate with [ServiceContract] + [DefaultServiceRoute] + [AspNetCompatibilityRequirements].
///
/// Each endpoint method needs:
///   [OperationContract]
///   [WebInvoke(Method = "GET"|"POST", RequestFormat/ResponseFormat = WebMessageFormat.Json,
///              BodyStyle = WebMessageBodyStyle.Wrapped)]
///
/// Namespace must follow the pattern Terrasoft.Configuration.{ServiceName}Namespace —
/// Creatio discovers services only within namespaces matching this convention.
///
/// URL pattern after deployment:
///   GET /0/ServiceModel/ContactLookupService.svc/GetContactIdByName?Name=John
///
/// POST body must be JSON-wrapped:  { "Name": "John" }
/// (BodyStyle.Wrapped adds an extra object layer — use BodyStyle.Bare for naked JSON)
/// </summary>
namespace Terrasoft.Configuration.ContactLookupServiceNamespace {

    [ServiceContract]
    [DefaultServiceRoute]
    [AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Required)]
    public class ContactLookupService : BaseService {

        [OperationContract]
        [WebInvoke(Method = "GET",
            RequestFormat  = WebMessageFormat.Json,
            BodyStyle      = WebMessageBodyStyle.Wrapped,
            ResponseFormat = WebMessageFormat.Json)]
        public string GetContactIdByName(string name) {
            var esq = new EntitySchemaQuery(UserConnection.EntitySchemaManager, "Contact");
            var idCol = esq.AddColumn("Id");
            esq.AddColumn("Name");
            esq.Filters.Add(
                esq.CreateFilterWithParameters(FilterComparisonType.Equal, "Name", name));

            var entities = esq.GetEntityCollection(UserConnection);
            if (entities.Count == 0)
                return string.Empty;

            return entities[0].GetTypedColumnValue<Guid>(idCol.Name).ToString();
        }
    }
}
