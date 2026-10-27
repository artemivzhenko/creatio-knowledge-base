import { Injectable } from '@angular/core';
import { HttpClientService } from '@creatio-devkit/common';

/** Response of the configuration web service; shape is yours to define. */
export interface MyDataResponse {
  value: string;
}

/**
 * Angular service injected into a request handler through its constructor.
 * Handlers get DI because bootstrapCrtModule() is given `resolveDependency`
 * backed by the module injector (see app.module.ts) - without it the
 * constructor arguments arrive as undefined.
 *
 * HttpClientService sends the request with the current user's session, so a
 * relative /rest/... url reaches a configuration web service of this site.
 */
@Injectable({ providedIn: 'root' })
export class MyDataService {
  private readonly _http = new HttpClientService();

  public async getValue(recordId: string): Promise<string> {
    const response = await this._http.post<MyDataResponse>(
      '/rest/UsrMyService/GetValue',
      { recordId },
      {},
    );
    return response.body?.value ?? '';
  }
}
