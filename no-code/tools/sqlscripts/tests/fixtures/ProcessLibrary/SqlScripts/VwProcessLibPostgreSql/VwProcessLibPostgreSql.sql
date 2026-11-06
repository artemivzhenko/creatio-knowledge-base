/*
** Project: BPMonline
** DBMS   : PostgreSql
** Type   : Script
** Name   : VwProcessLib
*/
CREATE OR REPLACE VIEW public."VwProcessLib"
AS
SELECT
	"VwSysSchemaInWorkspace"."UId" AS "Id"
	,"VwSysSchemaInWorkspace"."Id" AS "SysSchemaId"
	,"VwSysSchemaInWorkspace"."CreatedOn"
	,"VwSysSchemaInWorkspace"."CreatedById"
	,"VwSysSchemaInWorkspace"."ModifiedOn"
	,"VwSysSchemaInWorkspace"."ModifiedById"
	,"VwSysSchemaInWorkspace"."ProcessListeners"
	,"VwSysSchemaInWorkspace"."Name"
	,"VwSysSchemaInWorkspace"."Caption"
	,"VwSysSchemaInWorkspace"."ManagerName"
	,"VwSysSchemaInWorkspace"."UId"
	,"VwSysSchemaInWorkspace"."ParentId"
	,"VwSysSchemaInWorkspace"."ExtendParent"
	,"VwSysSchemaInWorkspace"."IsChanged"
	,"VwSysSchemaInWorkspace"."IsLocked"
	,"VwSysSchemaInWorkspace"."MetaData"
	,"VwSysSchemaInWorkspace"."MetaDataModifiedOn"
	,"VwSysSchemaInWorkspace"."SysPackageId"
	,"VwSysSchemaInWorkspace"."PackageUId"
	,"VwSysSchemaInWorkspace"."SysWorkspaceId"
	,"VwSysSchemaInWorkspace"."Description"
	,"VwSysSchemaInWorkspace"."NeedUpdateSourceCode"
	,"VwSysSchemaInWorkspace"."NeedUpdateStructure"
	,"VwSysSchemaInWorkspace"."NeedInstall"
	,COALESCE((
		SELECT TRUE
		FROM "SysSchemaProperty"
		WHERE "SysSchemaProperty"."SysSchemaId" = "VwSysSchemaInWorkspace"."Id"
		AND "SysSchemaProperty"."Name" = 'Version' AND "SysSchemaProperty"."Value" = (
			SELECT MAX("SysSchemaProperty"."Value")
			FROM "SysSchemaProperty"
			WHERE "SysSchemaProperty"."Name" = 'Version' AND "SysSchemaProperty"."SysSchemaId" IN (
				SELECT "VwSysSchemaInWorkspace"."Id"
				UNION
				SELECT "SysSchema"."Id"
				FROM "SysSchema"
				WHERE "SysSchema"."ParentId" IN ("VwSysSchemaInWorkspace"."ParentId", "VwSysSchemaInWorkspace"."Id")))
		), FALSE) AS "IsMaxVersion"
	,CASE
		WHEN EXISTS (
			SELECT
				"SysProcessDisabled"."Id"
			FROM "SysProcessDisabled"
			WHERE
				"SysProcessDisabled"."SysSchemaId" IN ("VwSysSchemaInWorkspace"."Id", "VwSysSchemaInWorkspace"."ParentId"))
			THEN FALSE
		ELSE TRUE
	END AS "Enabled"
	,"SysSchemaProperty"."Value" AS "TagProperty"
	,"VwPSV"."Version" AS "Version"
	,(SELECT "ProcessSchemaType"."Id"
		FROM public."ProcessSchemaType"
		WHERE (("ProcessSchemaType"."Code") = 'Business Process')) AS "ProcessSchemaTypeId"
	,(SELECT count("RunButtonProcessList"."Id") AS count
		FROM public."RunButtonProcessList"
		WHERE "RunButtonProcessList"."SysSchemaUId" = "VwSysSchemaInWorkspace"."UId")::bit(1) AS "AddToRunButton"
	,"VwPSV"."IsActiveVersion" AS "IsActiveVersion"
	,"VwPSV"."ParentId" AS "VersionParentId"
	,"VwPSV"."ParentUId" AS "VersionParentUId"
	,EXISTS (SELECT "SysPrcSchemaElement"."ProcessUId"
		FROM "SysPrcSchemaElement"
		WHERE "SysPrcSchemaElement"."ProcessUId" = "VwSysSchemaInWorkspace"."UId" AND "SysPrcSchemaElement"."StartType" = 1) AS "HasStartEvent"
	,public."fn_GetStartOptionsImageId"("VwSysSchemaInWorkspace"."UId") AS "StartOptionsImageId"
	,CASE
		WHEN ("VwSysSchemaInWorkspace"."ParentId" IS NULL) THEN public."fn_GetIsProcessTracing"("VwSysSchemaInWorkspace"."Id")
		ELSE public."fn_GetIsProcessTracing"("VwSysSchemaInWorkspace"."ParentId")
	END AS "IsProcessTracing"
FROM public."VwSysSchemaInWorkspace"
JOIN public."SysSchemaProperty" ON "SysSchemaProperty"."SysSchemaId" = "VwSysSchemaInWorkspace"."Id"
JOIN public."VwProcessSchemaVersion" AS "VwPSV" ON "VwPSV"."Id" = "VwSysSchemaInWorkspace"."Id"
WHERE "VwSysSchemaInWorkspace"."ManagerName" = 'ProcessSchemaManager' AND "SysSchemaProperty"."Name" = 'Tag' AND "SysSchemaProperty"."Value" <> '';