/**
 * Pure helper: determines the visibility and interactivity state of the
 * "Show Substitutes" checkbox in the ControlBar.
 *
 * Rules:
 *   substituteSettingOn=false          --> hidden (setting is off, no point showing)
 *   substituteSettingOn=true, no subs  --> visible but disabled with tooltip
 *   substituteSettingOn=true, has subs --> visible and enabled
 */

export interface SubstitutesCheckboxState {
  visible: boolean;
  disabled: boolean;
  tooltip: string | undefined;
}

export interface SubstitutesCheckboxInput {
  substituteSettingOn: boolean;
  hasSubstitutes: boolean;
}

/**
 * Returns the render state for the "Show Substitutes" checkbox.
 *
 * @example
 * getSubstitutesCheckboxState({ substituteSettingOn: false, hasSubstitutes: true })
 * // --> { visible: false, disabled: false, tooltip: undefined }
 *
 * @example
 * getSubstitutesCheckboxState({ substituteSettingOn: true, hasSubstitutes: false })
 * // --> { visible: true, disabled: true, tooltip: 'No substitute parts in this BOM' }
 *
 * @example
 * getSubstitutesCheckboxState({ substituteSettingOn: true, hasSubstitutes: true })
 * // --> { visible: true, disabled: false, tooltip: undefined }
 */
export function getSubstitutesCheckboxState({
  substituteSettingOn,
  hasSubstitutes
}: SubstitutesCheckboxInput): SubstitutesCheckboxState {
  if (!substituteSettingOn) {
    return { visible: false, disabled: false, tooltip: undefined };
  }

  if (!hasSubstitutes) {
    return {
      visible: true,
      disabled: true,
      tooltip: 'No substitute parts in this BOM'
    };
  }

  return { visible: true, disabled: false, tooltip: undefined };
}
