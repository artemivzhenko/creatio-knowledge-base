import { BaseRequest, BaseRequestHandler, CrtRequestHandler } from '@creatio-devkit/common';
import { MY_REQUEST } from '../requests/my.request';
import { PAGE_SCOPES } from './scopes';

/**
 * Intercepts a platform request - here page initialization - and raises the
 * custom request so the value is there when the page opens.
 *
 * Order matters: `this.next` first lets the platform finish initializing the
 * view model (attributes, data sources), so $context['Id'] is filled by the
 * time our request reads it.
 */
@CrtRequestHandler({
  type: 'usr.PageInitHandler',
  requestType: 'crt.HandleViewModelInitRequest',
  scopes: PAGE_SCOPES,
})
export class PageInitHandler extends BaseRequestHandler {
  public async handle(request: BaseRequest): Promise<unknown> {
    const result = await this.next?.handle(request);
    await this.handlerChain.process({
      type: MY_REQUEST,
      $context: request.$context,
    } as BaseRequest);
    return result;
  }
}
