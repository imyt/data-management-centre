import React from "react";
import { Plus, Minus, Info } from "lucide-react";
import type { AssetType, AssetTypeAttributeAssignmentRead } from "@/api/client";
import { dynamicAttributeFormStyles as styles } from "./DynamicAttributeForm.styles";

export interface DynamicAttributeFormProps {
  /** The selected Asset Type containing attribute assignments */
  assetType?: AssetType | null;
  /** Explicit assignments override if not passing assetType */
  attributeAssignments?: AssetTypeAttributeAssignmentRead[];
  /** Current attribute values mapped by attribute code */
  values: Record<string, any>;
  /** Callback fired when any attribute value changes */
  onChange: (values: Record<string, any>) => void;
  /** Validation errors keyed by attribute code */
  errors?: Record<string, string>;
  /** Disables all form controls */
  disabled?: boolean;
}

interface SelectOption {
  value: string;
  label: string;
}

function parseAllowedValues(raw: unknown): SelectOption[] {
  if (!raw) return [];
  let parsed = raw;
  if (typeof raw === "string") {
    try {
      parsed = JSON.parse(raw);
    } catch {
      return [{ value: raw, label: raw }];
    }
  }
  if (Array.isArray(parsed)) {
    return parsed.map((item) => {
      if (typeof item === "object" && item !== null) {
        const val = (item as any).value ?? (item as any).code ?? (item as any).id ?? String(item);
        const label = (item as any).label ?? (item as any).name ?? String(val);
        return { value: String(val), label: String(label) };
      }
      return { value: String(item), label: String(item) };
    });
  }
  return [];
}

export const DynamicAttributeForm: React.FC<DynamicAttributeFormProps> = ({
  assetType,
  attributeAssignments,
  values,
  onChange,
  errors = {},
  disabled = false,
}) => {
  const assignments = React.useMemo(() => {
    const list = attributeAssignments || assetType?.attribute_assignments || [];
    return [...list].sort((a, b) => a.display_order - b.display_order);
  }, [attributeAssignments, assetType]);

  const handleFieldChange = (code: string, value: any) => {
    onChange({
      ...values,
      [code]: value,
    });
  };

  const handleNumberStep = (code: string, delta: number) => {
    const current = typeof values[code] === "number" ? values[code] : 0;
    handleFieldChange(code, current + delta);
  };

  const handleMultiSelectToggle = (code: string, optionValue: string) => {
    const currentList: string[] = Array.isArray(values[code]) ? [...values[code]] : [];
    const index = currentList.indexOf(optionValue);
    if (index >= 0) {
      currentList.splice(index, 1);
    } else {
      currentList.push(optionValue);
    }
    handleFieldChange(code, currentList);
  };

  if (assignments.length === 0) {
    return (
      <div className={styles.emptyState}>
        No custom metamodel attributes assigned to this asset type.
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.sectionHeader}>
        <span className={styles.sectionTitle}>Metamodel Attributes</span>
        <span className={styles.badgeCount}>{assignments.length}</span>
      </div>

      <div className={styles.fieldsGrid}>
        {assignments.map((assignment) => {
          const attr = assignment.attribute_type;
          const code = attr.code;
          const dataType = (attr.data_type || "STRING").toUpperCase();
          const isRequired = assignment.is_required;
          const fieldError = errors[code];
          const rawValue = values[code];

          const isFullWidth = dataType === "MARKDOWN" || dataType === "MULTI_SELECT";
          const fieldWrapperClass = isFullWidth ? styles.fullWidthField : styles.halfWidthField;

          return (
            <div key={assignment.id || code} className={fieldWrapperClass}>
              {/* Field Label & Description */}
              <div className={styles.labelRow}>
                <label className={styles.label} htmlFor={`attr-${code}`}>
                  <span>{attr.name}</span>
                  {isRequired && <span className={styles.requiredStar}>*</span>}
                </label>
                {attr.description && (
                  <span className={styles.description} title={attr.description}>
                    <Info className="w-3 h-3 inline-block opacity-70" />
                  </span>
                )}
              </div>

              {/* Render by Data Type */}
              {dataType === "BOOLEAN" || dataType === "BOOL" ? (
                /* Boolean Switch */
                <div className={styles.switchContainer}>
                  <label
                    htmlFor={`attr-${code}`}
                    className={styles.switchLabelText}
                  >
                    {rawValue ? "Enabled / Yes" : "Disabled / No"}
                  </label>
                  <button
                    type="button"
                    id={`attr-${code}`}
                    role="switch"
                    aria-checked={Boolean(rawValue)}
                    disabled={disabled}
                    onClick={() => handleFieldChange(code, !Boolean(rawValue))}
                    className={`${styles.switchTrack} ${
                      rawValue ? styles.switchTrackActive : styles.switchTrackInactive
                    }`}
                  >
                    <span
                      className={`${styles.switchThumb} ${
                        rawValue ? styles.switchThumbActive : styles.switchThumbInactive
                      }`}
                    />
                  </button>
                </div>
              ) : dataType === "NUMBER" || dataType === "INT" || dataType === "FLOAT" ? (
                /* Number Stepper */
                <div className={styles.numberStepperWrapper}>
                  <input
                    type="number"
                    id={`attr-${code}`}
                    disabled={disabled}
                    value={rawValue !== undefined && rawValue !== null ? rawValue : ""}
                    onChange={(e) => {
                      const val = e.target.value === "" ? undefined : Number(e.target.value);
                      handleFieldChange(code, val);
                    }}
                    placeholder={assignment.default_value || "0"}
                    className={styles.numberInput}
                  />
                  <div className={styles.stepperButtons}>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => handleNumberStep(code, -1)}
                      className={styles.stepperButton}
                      title="Decrease"
                    >
                      <Minus className="w-3 h-3" />
                    </button>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => handleNumberStep(code, 1)}
                      className={styles.stepperButton}
                      title="Increase"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ) : dataType === "ENUM" || dataType === "SINGLE_SELECT" ? (
                /* Dropdown Select */
                <select
                  id={`attr-${code}`}
                  disabled={disabled}
                  value={rawValue !== undefined && rawValue !== null ? String(rawValue) : ""}
                  onChange={(e) => handleFieldChange(code, e.target.value)}
                  className={styles.select}
                >
                  <option value="">
                    {isRequired ? `-- Select ${attr.name} --` : `-- None --`}
                  </option>
                  {parseAllowedValues(attr.allowed_values).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              ) : dataType === "MULTI_SELECT" || dataType === "MULTISELECT" ? (
                /* Multi Select Checkbox Box */
                <div className={styles.multiSelectBox}>
                  {parseAllowedValues(attr.allowed_values).length === 0 ? (
                    <div className="text-muted-foreground text-[11px] p-1">No options defined</div>
                  ) : (
                    parseAllowedValues(attr.allowed_values).map((opt) => {
                      const selected = Array.isArray(rawValue) && rawValue.includes(opt.value);
                      return (
                        <label
                          key={opt.value}
                          className={styles.multiSelectRow}
                        >
                          <input
                            type="checkbox"
                            disabled={disabled}
                            checked={selected}
                            onChange={() => handleMultiSelectToggle(code, opt.value)}
                            className={styles.multiCheckbox}
                          />
                          <span>{opt.label}</span>
                        </label>
                      );
                    })
                  )}
                </div>
              ) : dataType === "DATE" || dataType === "DATETIME" ? (
                /* Date Input */
                <input
                  type="date"
                  id={`attr-${code}`}
                  disabled={disabled}
                  value={rawValue || ""}
                  onChange={(e) => handleFieldChange(code, e.target.value)}
                  className={styles.dateInput}
                />
              ) : dataType === "MARKDOWN" ? (
                /* Markdown Textarea */
                <textarea
                  id={`attr-${code}`}
                  rows={3}
                  disabled={disabled}
                  value={rawValue || ""}
                  onChange={(e) => handleFieldChange(code, e.target.value)}
                  placeholder={assignment.default_value || `Enter ${attr.name.toLowerCase()}...`}
                  className={styles.textarea}
                />
              ) : (
                /* Default Text Input */
                <input
                  type="text"
                  id={`attr-${code}`}
                  disabled={disabled}
                  value={rawValue !== undefined && rawValue !== null ? String(rawValue) : ""}
                  onChange={(e) => handleFieldChange(code, e.target.value)}
                  placeholder={assignment.default_value || `Enter ${attr.name.toLowerCase()}...`}
                  className={styles.input}
                />
              )}

              {/* Error Message */}
              {fieldError && <div className={styles.errorText}>{fieldError}</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
};
