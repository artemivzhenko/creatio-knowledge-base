/* Import the required functionality from the libraries. */
import { Component, EventEmitter, Input, OnInit, Output, ViewEncapsulation } from '@angular/core';
import { CrtInput, CrtInterfaceDesignerItem, CrtOutput, CrtValidationInfo, CrtValidationInput, CrtViewElement } from '@creatio-devkit/common';

@Component({
  selector: 'usr-input',
  templateUrl: './input.component.html',
  styleUrls: ['./input.component.scss'],
  encapsulation: ViewEncapsulation.ShadowDom
})

/* Add the CrtViewElement decorator to the InputComponent component. */
@CrtViewElement({
  selector: 'usr-input',
  type: 'usr.Input'
})

/* Add the CrtViewElement to the InputComponent component. */
@CrtInterfaceDesignerItem({
  /* Manages the element layout in the library of the Freedom UI Designer. */
  toolbarConfig: {
    caption: 'Custom Input',
      name: 'CustomInput',
      /* The path to the component image. */
      icon: require('!!raw-loader?{esModule:false}!./icon.svg'),
      defaultPropertyValues: {
        label: 'Custom input'
      }
  }
})

export class InputComponent implements OnInit {
  constructor() { }

  /* Add decorators to the value property. */
  @Input()
  @CrtInput()
  /* The input value. */
  public value: string = '';

  /* Add decorators to the label property. */
  @Input()
  @CrtInput()
  /* The input name. */
  public label!: string;

  /* Add decorators to the EventEmitter<string>() event. */
  @Output()
  @CrtOutput()
  /* Track input value changes. */
  public valueChange = new EventEmitter<string>();

  /* Add decorators to the valueValidationInfo property. */
  @Input()
  @CrtValidationInput()
  /* Display information that the input value is invalid. */ 
  public valueValidationInfo!: CrtValidationInfo;

  ngOnInit(): void {
  }
}