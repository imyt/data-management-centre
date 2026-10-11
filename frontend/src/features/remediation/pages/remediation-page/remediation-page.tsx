import React from "react";
import { RemediationHub } from "../../components/RemediationHub";
import { remediationPageStyles } from "./remediation-page.styles";

export const RemediationPage: React.FC = () => {
  return (
    <div className={remediationPageStyles.container}>
      <RemediationHub />
    </div>
  );
};
