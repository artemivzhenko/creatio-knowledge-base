import {
	BaseRequestHandler,
	CrtRequestHandler,
	HandleViewModelAttributeChangeRequest,
	Logger,
} from '@creatio/mobile-common';
import { PAGE_SCOPES } from '../config/scopes';

const WATCHED_ATTRIBUTE = 'PDS_UsrName_a1b2c3d';

/**
 * Intercepts a platform request - here the field-change event - and reacts to
 * one attribute only. Every other change passes through untouched.
 *
 * The same shape intercepts any crt.* request (crt.SaveRecordRequest,
 * crt.SetAttributeFromBarcodeRequest, ...). Call `this.next` unless you fully
 * replaced the platform behaviour, otherwise the stock logic runs twice.
 */
@CrtRequestHandler({
	type: 'usr.AttributeChangeRequestHandler',
	requestType: 'crt.HandleViewModelAttributeChangeRequest',
	scopes: PAGE_SCOPES,
})
export class UsrAttributeChangeRequestHandler extends BaseRequestHandler<HandleViewModelAttributeChangeRequest> {
	public async handle(request: HandleViewModelAttributeChangeRequest): Promise<unknown> {
		if (request.attributeName !== WATCHED_ATTRIBUTE) {
			return this.next?.handle(request);
		}
		Logger.console(`[UsrMobileModule] ${WATCHED_ATTRIBUTE}: ${request.oldValue} -> ${request.value}`);
		// React here, then let the platform finish its own processing of the change.
		return this.next?.handle(request);
	}
}
