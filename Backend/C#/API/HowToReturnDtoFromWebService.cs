using System.Collections.Generic;
using System.Runtime.Serialization;
using System.ServiceModel;
using System.ServiceModel.Activation;
using System.ServiceModel.Web;
using Terrasoft.Web.Common;

/// <summary>
/// Pattern: return structured data from a custom web service using DTO classes.
///
/// Use [DataContract] / [DataMember] to define the exact JSON shape the client receives.
/// This decouples the API contract from internal domain objects and makes the serialized
/// output explicit — no accidental property leakage, no dependency on field naming conventions.
///
/// Rules:
///   - DTO class must be public with a public parameterless constructor.
///   - Every serialized property needs [DataMember]; un-annotated properties are ignored.
///   - Name = "..." in [DataMember] sets the exact JSON key — use camelCase for JS clients.
///   - Complex types (lists, nested DTOs) are supported as long as they are also [DataContract].
///
/// Namespace must follow the pattern Terrasoft.Configuration.{ServiceName}Namespace.
/// </summary>
namespace Terrasoft.Configuration.ContactApiServiceNamespace {

    // ── DTO definitions ───────────────────────────────────────────────────────

    [DataContract]
    public class ContactDto {

        [DataMember(Name = "id")]
        public string Id { get; set; }

        [DataMember(Name = "name")]
        public string Name { get; set; }

        [DataMember(Name = "email")]
        public string Email { get; set; }
    }

    [DataContract]
    public class ContactListResponse {

        [DataMember(Name = "items")]
        public List<ContactDto> Items { get; set; }

        [DataMember(Name = "total")]
        public int Total { get; set; }
    }

    // ── Service ───────────────────────────────────────────────────────────────

    [ServiceContract]
    [DefaultServiceRoute]
    [AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Required)]
    public class ContactApiService : BaseService {

        // GET /0/ServiceModel/ContactApiService.svc/GetContact?id=...
        [OperationContract]
        [WebInvoke(Method = "GET",
            RequestFormat  = WebMessageFormat.Json,
            BodyStyle      = WebMessageBodyStyle.Wrapped,
            ResponseFormat = WebMessageFormat.Json)]
        public ContactDto GetContact(string id) {
            // load entity, map to DTO
            return new ContactDto {
                Id    = id,
                Name  = "John Smith",
                Email = "john@example.com"
            };
        }

        // GET /0/ServiceModel/ContactApiService.svc/GetContacts
        [OperationContract]
        [WebInvoke(Method = "GET",
            RequestFormat  = WebMessageFormat.Json,
            BodyStyle      = WebMessageBodyStyle.Wrapped,
            ResponseFormat = WebMessageFormat.Json)]
        public ContactListResponse GetContacts() {
            var items = new List<ContactDto> {
                new ContactDto { Id = "1", Name = "Alice", Email = "alice@example.com" },
                new ContactDto { Id = "2", Name = "Bob",   Email = "bob@example.com"   }
            };

            return new ContactListResponse {
                Items = items,
                Total = items.Count
            };
        }
    }
}
