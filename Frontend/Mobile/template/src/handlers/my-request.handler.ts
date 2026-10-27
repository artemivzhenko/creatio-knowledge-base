import { BaseRequestHandler, CrtRequestHandler, HandlerChainService, Logger } from '@creatio/mobile-common';
import { PAGE_SCOPES } from '../config/scopes';
import { MY_REQUEST, UsrMyRequest } from '../requests/my-request';

/** The generated page attribute name, read off the real schema (not the column name). */
const DEFAULT_ATTRIBUTE = 'PDS_UsrName_a1b2c3d';

/**
 * Handles the custom request: reads an attribute, writes it back and runs a
 * stock request through HandlerChainService. Replace the body with real logic.
 */
@CrtRequestHandler({
	type: 'usr.MyRequestHandler',
	requestType: MY_REQUEST,
	scopes: PAGE_SCOPES,
})
export class UsrMyRequestHandler extends BaseRequestHandler<UsrMyRequest> {
	public async handle(request: UsrMyRequest): Promise<unknown> {
		const attributeName = request.attributeName ?? DEFAULT_ATTRIBUTE;
		const current = await request.$context.getAttribute(attributeName);
		Logger.console(`[UsrMobileModule] ${MY_REQUEST}: ${attributeName} = ${JSON.stringify(current)}`);

		await request.$context.setAttribute(attributeName, `${current ?? ''}`.trim());

		// Any stock request can be raised from a handler, e.g. a business process.
		await HandlerChainService.instance.process({
			type: 'crt.RunBusinessProcessRequest',
			$context: request.$context,
			processName: 'UsrMyProcess',
			processParameters: { RecordId: await request.$context.getAttribute('Id') },
			resultParameterNames: [],
			saveAtProcessStart: false,
			showNotification: false,
		} as never);

		// This request is ours alone, so no platform handler follows; passing it
		// on costs nothing and keeps other modules' handlers working.
		return this.next?.handle(request);
	}
}
