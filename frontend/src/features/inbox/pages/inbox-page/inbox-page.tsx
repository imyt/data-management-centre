import React from "react";
import { GovernanceInbox } from "../../components/GovernanceInbox";
import { inboxPageStyles } from "./inbox-page.styles";

export const InboxPage: React.FC = () => {
  return (
    <div className={inboxPageStyles.container}>
      <GovernanceInbox />
    </div>
  );
};
