namespace Terrasoft.Configuration
{
	using System;
	using System.Linq;
	using Terrasoft.Core;
	using Terrasoft.Core.Entities;
	using Terrasoft.Core.Entities.Events;

	#region Class: UsrOrderEventListener

	/// <summary>Order rules applied on every save: a new order gets the "New" status; a negative amount is refused.</summary>
	[EntityEventListener(SchemaName = "UsrOrder")]
	public class UsrOrderEventListener : BaseEntityEventListener
	{

		#region Constants: Public

		public const string DefaultStatusName = "New";
		public const string NegativeAmountMessage = "The order amount must not be negative";

		#endregion

		#region Methods: Private

		private static Guid FindStatusId(UserConnection userConnection, string statusName) {
			var esq = new EntitySchemaQuery(userConnection.EntitySchemaManager, "UsrOrderStatus");
			string idColumn = esq.AddColumn("Id").Name;
			esq.Filters.Add(esq.CreateFilterWithParameters(FilterComparisonType.Equal, "Name", statusName));
			Entity status = esq.GetEntityCollection(userConnection).FirstOrDefault();
			return status == null ? Guid.Empty : status.GetTypedColumnValue<Guid>(idColumn);
		}

		#endregion

		#region Methods: Public

		public override void OnInserting(object sender, EntityBeforeEventArgs e) {
			base.OnInserting(sender, e);
			var order = (Entity)sender;
			// A column nobody set is "not loaded": reading it throws instead of returning the default.
			if (order.IsColumnValueLoaded("UsrStatusId") && order.GetTypedColumnValue<Guid>("UsrStatusId") != Guid.Empty) {
				return;
			}
			Guid statusId = FindStatusId(order.UserConnection, DefaultStatusName);
			if (statusId != Guid.Empty) {
				order.SetColumnValue("UsrStatusId", statusId);
			}
		}

		public override void OnSaving(object sender, EntityBeforeEventArgs e) {
			base.OnSaving(sender, e);
			var order = (Entity)sender;
			if (order.IsColumnValueLoaded("UsrAmount") && order.GetTypedColumnValue<decimal>("UsrAmount") < 0) {
				throw new InvalidOperationException(NegativeAmountMessage);
			}
		}

		#endregion

	}

	#endregion

}
