using System;
using System.Collections.Generic;
using FluentAssertions;
using NUnit.Framework;
using Terrasoft.Configuration;
using Terrasoft.Configuration.Tests;
using Terrasoft.Core.Entities;
using Terrasoft.Core.Entities.Events;

/// <summary>
/// Demonstrates how to unit-test an entity event listener (or any UserConnection-bound class) with no
/// Creatio instance: the test project clio scaffolds (`clio new-test-project --package UsrPkg`, run from
/// the workspace root) ships Creatio's own test kit - `BaseConfigurationTestFixture` gives a fake
/// `UserConnection`, `MockEntitySchemaWithColumns` declares the schemas the code touches,
/// `CreateEntity` builds a real Entity on them and `SetUpTestData` serves the rows an ESQ would read.
/// The listener is then called the way the platform calls it: `OnInserting(entity, new EntityBeforeEventArgs())`.
/// Two attributes are mandatory, or SetUp dies with a NullReferenceException:
/// `[EntityManagerSettings(EntityManagerMode.ReinitByCustomSchemas)]` installs the test schema manager the
/// Mock* helpers cast to, `[MockSettings(RequireMock.All)]` wires the DB engine, resources and current user doubles.
/// Trap the kit reproduces faithfully: a column nobody set is "not loaded" and `GetTypedColumnValue` throws
/// `InvalidObjectStateException` (NotLoadedColumnValue) - guard with `IsColumnValueLoaded` first.
/// Out of reach without an instance: `Entity.Save`, raw `Select`/`Insert` against the DB, DcmSchemaManager,
/// `EnsureDBConnection` - prove those over OData from outside instead.
/// Run with `dotnet test tests/UsrPkg/UsrPkg.Tests.csproj -c dev-nf` (net472) or `-c dev-n8` (.NET 8).
/// </summary>
namespace UsrPkg.Tests {

	// The listener under test, in the package's Files/cs:
	//
	//   [EntityEventListener(SchemaName = "UsrOrder")]
	//   public class UsrOrderEventListener : BaseEntityEventListener {
	//       public override void OnInserting(object sender, EntityBeforeEventArgs e) {
	//           base.OnInserting(sender, e);
	//           var order = (Entity)sender;
	//           if (order.IsColumnValueLoaded("UsrStatusId") && order.GetTypedColumnValue<Guid>("UsrStatusId") != Guid.Empty) {
	//               return;
	//           }
	//           var esq = new EntitySchemaQuery(order.UserConnection.EntitySchemaManager, "UsrOrderStatus");
	//           string idColumn = esq.AddColumn("Id").Name;
	//           esq.Filters.Add(esq.CreateFilterWithParameters(FilterComparisonType.Equal, "Name", "New"));
	//           Entity status = esq.GetEntityCollection(order.UserConnection).FirstOrDefault();
	//           if (status != null) {
	//               order.SetColumnValue("UsrStatusId", status.GetTypedColumnValue<Guid>(idColumn));
	//           }
	//       }
	//   }

	[TestFixture]
	[EntityManagerSettings(EntityManagerMode.ReinitByCustomSchemas)]
	[MockSettings(RequireMock.All)]
	public class UsrOrderEventListenerTests : BaseComposableAppTestFixture {

		private static readonly Guid NewStatusId = new Guid("11111111-1111-1111-1111-111111111111");
		private static readonly Guid OtherStatusId = new Guid("22222222-2222-2222-2222-222222222222");

		[SetUp]
		public void SetUpSchemas() {
			// Only the columns the code reads or writes; lookups go in the second dictionary as column -> schema.
			MockEntitySchemaWithColumns("UsrOrderStatus",
				new Dictionary<string, DataValueType> { { "Name", DataValueType.Text } });
			MockEntitySchemaWithColumns("UsrOrder",
				new Dictionary<string, DataValueType> {
					{ "UsrName", DataValueType.Text },
					{ "UsrAmount", DataValueType.Money }
				},
				new Dictionary<string, string> { { "UsrStatus", "UsrOrderStatus" } });
			// Every ESQ on UsrOrderStatus returns this row, whatever its filter.
			SetUpTestData("UsrOrderStatus", new Dictionary<string, object> {
				{ "Id", NewStatusId },
				{ "Name", "New" }
			});
		}

		private Entity CreateOrder(Guid statusId) {
			var columns = new Dictionary<string, object> { { "UsrName", "Order under test" }, { "UsrAmount", 100m } };
			if (statusId != Guid.Empty) {
				columns["UsrStatusId"] = statusId;
			}
			return CreateEntity("UsrOrder", columns);
		}

		[Test]
		public void OnInserting_SetsTheNewStatus_WhenTheOrderHasNone() {
			Entity order = CreateOrder(Guid.Empty);

			new UsrOrderEventListener().OnInserting(order, new EntityBeforeEventArgs());

			order.GetTypedColumnValue<Guid>("UsrStatusId").Should().Be(NewStatusId);
		}

		[Test]
		public void OnInserting_KeepsTheStatus_WhenTheOrderHasOne() {
			Entity order = CreateOrder(OtherStatusId);

			new UsrOrderEventListener().OnInserting(order, new EntityBeforeEventArgs());

			order.GetTypedColumnValue<Guid>("UsrStatusId").Should().Be(OtherStatusId);
		}

		[Test]
		public void OnSaving_Refuses_ANegativeAmount() {
			Entity order = CreateEntity("UsrOrder", new Dictionary<string, object> { { "UsrAmount", -1m } });

			Action save = () => new UsrOrderEventListener().OnSaving(order, new EntityBeforeEventArgs());

			save.Should().Throw<InvalidOperationException>();
		}

	}

}
