namespace Terrasoft.Configuration.UsrOrderServiceNamespace
{
	using System;
	using System.Runtime.Serialization;
	using System.ServiceModel;
	using System.ServiceModel.Activation;
	using System.ServiceModel.Web;
	using Terrasoft.Core;
	using Terrasoft.Core.Entities;
	using Terrasoft.Web.Common;

	#region Class: OrderLabelResponse

	[DataContract]
	public class OrderLabelResponse
	{
		[DataMember(Name = "success")]
		public bool Success { get; set; } = true;

		[DataMember(Name = "label", EmitDefaultValue = false)]
		public string Label { get; set; }
	}

	#endregion

	#region Class: UsrOrderService

	/// <summary>Thin API over the Files/cs classes: the label of an order, by id.</summary>
	[ServiceContract]
	[AspNetCompatibilityRequirements(RequirementsMode = AspNetCompatibilityRequirementsMode.Required)]
	public class UsrOrderService : BaseService
	{

		#region Methods: Private

		private Entity ReadOrder(Guid orderId) {
			var esq = new EntitySchemaQuery(UserConnection.EntitySchemaManager, "UsrOrder");
			esq.AddAllSchemaColumns();
			return esq.GetEntity(UserConnection, orderId); // null when the id isn't an order's
		}

		#endregion

		#region Methods: Public

		[OperationContract]
		[WebInvoke(Method = "GET", UriTemplate = "label/{orderId}", ResponseFormat = WebMessageFormat.Json)]
		public OrderLabelResponse GetLabel(string orderId) {
			Entity order = ReadOrder(Guid.Parse(orderId));
			if (order == null) {
				return new OrderLabelResponse { Success = false, Label = "{no such order}" };
			}
			return new OrderLabelResponse { Label = UsrOrderLabel.Build(order.GetTypedColumnValue<string>("UsrType"), order.GetTypedColumnValue<int>("UsrSeq")) };
		}

		[OperationContract]
		[WebInvoke(Method = "POST", UriTemplate = "rebuild", ResponseFormat = WebMessageFormat.Json)]
		public int RebuildAll() {
			var update = new Update(UserConnection, "UsrOrder").Set("UsrLabel", Column.Parameter(string.Empty));
			return update.Execute();
		}

		#endregion

	}

	#endregion

}
