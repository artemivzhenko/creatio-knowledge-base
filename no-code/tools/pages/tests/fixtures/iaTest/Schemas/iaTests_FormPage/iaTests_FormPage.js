define("iaTests_FormPage", /**SCHEMA_DEPS*/[]/**SCHEMA_DEPS*/, function/**SCHEMA_ARGS*/()/**SCHEMA_ARGS*/ {
	return {
		viewConfigDiff: /**SCHEMA_VIEW_CONFIG_DIFF*/[
			{
				"operation": "insert",
				"name": "iaName",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 1,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.Input",
					"label": "$Resources.Strings.iaName",
					"control": "$iaName",
					"labelPosition": "auto"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 0
			},
			{
				"operation": "insert",
				"name": "iaComment",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 2,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.Input",
					"label": "$Resources.Strings.iaComment",
					"control": "$iaComment",
					"labelPosition": "auto"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 1
			},
			{
				"operation": "insert",
				"name": "iaNumber",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 3,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.NumberInput",
					"label": "$Resources.Strings.iaNumber",
					"control": "$iaNumber",
					"labelPosition": "auto"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 2
			},
			{
				"operation": "insert",
				"name": "iaAmount",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 4,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.NumberInput",
					"label": "$Resources.Strings.iaAmount",
					"control": "$iaAmount",
					"labelPosition": "auto"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 3
			},
			{
				"operation": "insert",
				"name": "iaIsActive",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 5,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.Checkbox",
					"label": "$Resources.Strings.iaIsActive",
					"control": "$iaIsActive",
					"labelPosition": "auto"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 4
			},
			{
				"operation": "insert",
				"name": "iaDate",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 6,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.DateTimePicker",
					"label": "$Resources.Strings.iaDate",
					"control": "$iaDate",
					"labelPosition": "auto",
					"pickerType": "date"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 5
			},
			{
				"operation": "insert",
				"name": "iaDateTime",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 7,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.DateTimePicker",
					"label": "$Resources.Strings.iaDateTime",
					"control": "$iaDateTime",
					"labelPosition": "auto",
					"pickerType": "datetime"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 6
			},
			{
				"operation": "insert",
				"name": "iaOnlyDate",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 8,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.DateTimePicker",
					"label": "$Resources.Strings.iaOnlyDate",
					"control": "$iaOnlyDate",
					"labelPosition": "auto",
					"pickerType": "date"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 7
			},
			{
				"operation": "insert",
				"name": "iaContactLookup",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 9,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.ComboBox",
					"label": "$Resources.Strings.iaContactLookup",
					"control": "$iaContactLookup",
					"labelPosition": "auto"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 8
			},
			{
				"operation": "insert",
				"name": "iaAccount",
				"values": {
					"layoutConfig": {
						"column": 1,
						"row": 10,
						"colSpan": 1,
						"rowSpan": 1
					},
					"type": "crt.ComboBox",
					"label": "$Resources.Strings.iaAccount",
					"control": "$iaAccount",
					"labelPosition": "auto"
				},
				"parentName": "SideAreaProfileContainer",
				"propertyName": "items",
				"index": 9
			},
			{
				"operation": "merge",
				"name": "AttachmentList",
				"values": {
					"type": "crt.FileList",
					"masterRecordColumnValue": "$Id",
					"recordColumnName": "RecordId",
					"layoutConfig": {
						"colSpan": 2,
						"column": 1,
						"row": 1,
						"rowSpan": 6
					},
					"items": "$AttachmentList",
					"primaryColumnName": "AttachmentListDS_Id",
					"columns": [
						{
							"id": "76140cd6-75e3-438d-9de5-c652bee20af0",
							"code": "AttachmentListDS_Name",
							"caption": "#ResourceString(AttachmentListDS_Name)#",
							"dataValueType": 28,
							"width": 200
						}
					],
					"viewType": "gallery",
					"tileSize": "small"
				},
				"parentName": "AttachmentsTabContainer",
				"propertyName": "items",
				"index": 0
			},
			{
				"operation": "merge",
				"name": "Feed",
				"values": {
					"type": "crt.Feed",
					"feedType": "Record",
					"primaryColumnValue": "$Id",
					"cardState": "$CardState",
					"dataSourceName": "PDS",
					"entitySchemaName": "iaTest"
				},
				"parentName": "FeedTabContainer",
				"propertyName": "items",
				"index": 0
			},
			{
				"operation": "insert",
				"name": "iaOrderList",
				"values": {
					"type": "crt.DataGrid",
					"columns": [
						{
							"id": "eb645dea-87f6-498b-9fdc-fe63849a3fd9",
							"code": "iaOrderListDS_iaName",
							"caption": "Name",
							"dataValueType": 28,
							"width": 200
						},
						{
							"id": "7d08a0a3-9ae8-4934-97ed-70fd92ade4aa",
							"code": "iaOrderListDS_iaQuantity",
							"caption": "Quantity",
							"dataValueType": 4,
							"width": 120
						}
					],
					"items": "$iaOrderList",
					"primaryColumnName": "iaOrderListDS_Id",
					"layoutConfig": {
						"column": 1,
						"row": 1,
						"colSpan": 2,
						"rowSpan": 6
					},
					"features": {
						"editable": {
							"enable": false
						},
						"rows": {
							"selection": {
								"enable": true,
								"multiple": true
							}
						}
					},
					"visible": true
				},
				"parentName": "GeneralInfoTabContainer",
				"propertyName": "items",
				"index": 0
			}
		]/**SCHEMA_VIEW_CONFIG_DIFF*/,
		viewModelConfig: /**SCHEMA_VIEW_MODEL_CONFIG*/{
			"attributes": {
				"iaName": {
					"modelConfig": {
						"path": "PDS.iaName"
					}
				},
				"iaComment": {
					"modelConfig": {
						"path": "PDS.iaComment"
					}
				},
				"iaNumber": {
					"modelConfig": {
						"path": "PDS.iaNumber"
					}
				},
				"iaAmount": {
					"modelConfig": {
						"path": "PDS.iaAmount"
					}
				},
				"iaIsActive": {
					"modelConfig": {
						"path": "PDS.iaIsActive"
					}
				},
				"iaDate": {
					"modelConfig": {
						"path": "PDS.iaDate"
					}
				},
				"iaDateTime": {
					"modelConfig": {
						"path": "PDS.iaDateTime"
					}
				},
				"iaOnlyDate": {
					"modelConfig": {
						"path": "PDS.iaOnlyDate"
					}
				},
				"iaContactLookup": {
					"modelConfig": {
						"path": "PDS.iaContactLookup"
					}
				},
				"iaAccount": {
					"modelConfig": {
						"path": "PDS.iaAccount"
					}
				},
				"Id": {
					"modelConfig": {
						"path": "PDS.Id"
					}
				},
				"iaOrderList": {
					"isCollection": true,
					"modelConfig": {
						"path": "iaOrderListDS",
						"sortingConfig": {
							"default": [
								{
									"columnName": "iaName",
									"direction": "asc"
								}
							]
						}
					},
					"viewModelConfig": {
						"attributes": {
							"iaOrderListDS_iaName": {
								"modelConfig": {
									"path": "iaOrderListDS.iaName"
								}
							},
							"iaOrderListDS_iaQuantity": {
								"modelConfig": {
									"path": "iaOrderListDS.iaQuantity"
								}
							},
							"iaOrderListDS_Id": {
								"modelConfig": {
									"path": "iaOrderListDS.Id"
								}
							}
						}
					}
				}
			}
		}/**SCHEMA_VIEW_MODEL_CONFIG*/,
		modelConfig: /**SCHEMA_MODEL_CONFIG*/{
			"dataSources": {
				"PDS": {
					"type": "crt.EntityDataSource",
					"config": {
						"entitySchemaName": "iaTest"
					},
					"scope": "page"
				},
				"AttachmentListDS": {
					"type": "crt.EntityDataSource",
					"scope": "viewElement",
					"config": {
						"entitySchemaName": "SysFile",
						"attributes": {
							"Name": {
								"path": "Name"
							}
						}
					}
				},
				"iaOrderListDS": {
					"type": "crt.EntityDataSource",
					"scope": "viewElement",
					"config": {
						"entitySchemaName": "iaOrder",
						"attributes": {
							"iaName": {
								"path": "iaName"
							},
							"iaQuantity": {
								"path": "iaQuantity"
							}
						}
					}
				}
			},
			"primaryDataSourceName": "PDS"
		}/**SCHEMA_MODEL_CONFIG*/,
		handlers: /**SCHEMA_HANDLERS*/[]/**SCHEMA_HANDLERS*/,
		converters: /**SCHEMA_CONVERTERS*/{}/**SCHEMA_CONVERTERS*/,
		validators: /**SCHEMA_VALIDATORS*/{}/**SCHEMA_VALIDATORS*/
	};
});
