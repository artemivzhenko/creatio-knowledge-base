import { BaseRequestHandler, CrtRequestHandler } from '@creatio-devkit/common';
import { MY_REQUEST, MyRequest } from '../requests/my.request';
import { MyDataService } from '../services/my-data.service';
import { PAGE_SCOPES } from './scopes';

/**
 * Handles the custom request: calls a service and writes the result into a
 * page attribute. A component bound to "$UsrMyValue" shows it.
 *
 * The page must declare the attribute in viewModelConfigDiff
 * ("UsrMyValue": {}) - writing an undeclared attribute is silently ignored.
 */
@CrtRequestHandler({
  type: 'usr.MyRequestHandler',
  requestType: MY_REQUEST,
  scopes: PAGE_SCOPES,
})
export class MyRequestHandler extends BaseRequestHandler<MyRequest> {
  constructor(private readonly _dataService: MyDataService) {
    super();
  }

  public async handle(request: MyRequest): Promise<unknown> {
    const recordId = request.recordId ?? await request.$context['Id'];
    const value = await this._dataService.getValue(recordId);
    request.$context['UsrMyValue'] = value;
    // The request is ours alone; passing it on keeps other handlers of the same
    // request type (another module, the page schema) working.
    return this.next?.handle(request);
  }
}
