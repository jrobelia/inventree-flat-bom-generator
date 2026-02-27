/**
 * Tests for getSubstitutesCheckboxState helper
 *
 * Tests the three visibility/state rules for the "Show Substitutes" checkbox:
 *   1. substituteSettingOn=false  --> hidden (visible=false)
 *   2. substituteSettingOn=true, hasSubstitutes=false --> visible, disabled, tooltip shown
 *   3. substituteSettingOn=true, hasSubstitutes=true  --> visible, enabled, no tooltip
 *
 * Pure function -- no React or DOM needed.
 *
 * NOTE: These tests are RED. The helper does not exist yet.
 * They will fail with "Cannot find module" until the implementation is created.
 */

import { describe, expect, it } from 'vitest';
import { getSubstitutesCheckboxState } from './substituteCheckboxState';

// ---------------------------------------------------------------------------
// Rule 1: substituteSettingOn is false --> checkbox must not be shown
// ---------------------------------------------------------------------------

describe('getSubstitutesCheckboxState -- when substituteSettingOn is false', () => {
  it('should return visible=false regardless of hasSubstitutes', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: false,
      hasSubstitutes: true
    });

    expect(result.visible).toBe(false);
  });

  it('should return visible=false when both flags are false', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: false,
      hasSubstitutes: false
    });

    expect(result.visible).toBe(false);
  });

  it('should not return a tooltip when setting is off', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: false,
      hasSubstitutes: false
    });

    expect(result.tooltip).toBeUndefined();
  });

  it('should return disabled=false when setting is off', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: false,
      hasSubstitutes: false
    });

    // disabled is irrelevant when not visible, but must not be true
    expect(result.disabled).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Rule 2: substituteSettingOn=true, hasSubstitutes=false --> disabled + tooltip
// ---------------------------------------------------------------------------

describe('getSubstitutesCheckboxState -- when setting on but no substitutes in BOM', () => {
  it('should return visible=true so the checkbox is rendered', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: true,
      hasSubstitutes: false
    });

    expect(result.visible).toBe(true);
  });

  it('should return disabled=true', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: true,
      hasSubstitutes: false
    });

    expect(result.disabled).toBe(true);
  });

  it('should return the exact tooltip text "No substitute parts in this BOM"', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: true,
      hasSubstitutes: false
    });

    expect(result.tooltip).toBe('No substitute parts in this BOM');
  });
});

// ---------------------------------------------------------------------------
// Rule 3: substituteSettingOn=true, hasSubstitutes=true --> enabled, no tooltip
// ---------------------------------------------------------------------------

describe('getSubstitutesCheckboxState -- when setting on and substitutes exist', () => {
  it('should return visible=true', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: true,
      hasSubstitutes: true
    });

    expect(result.visible).toBe(true);
  });

  it('should return disabled=false so the checkbox is interactive', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: true,
      hasSubstitutes: true
    });

    expect(result.disabled).toBe(false);
  });

  it('should not return a tooltip when the checkbox is usable', () => {
    const result = getSubstitutesCheckboxState({
      substituteSettingOn: true,
      hasSubstitutes: true
    });

    expect(result.tooltip).toBeUndefined();
  });
});
