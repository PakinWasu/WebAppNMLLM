import React, { useState, useEffect } from "react";
import { Field, Select, Button } from "./ui";

export default function AddMemberInline({
  members,
  onAdd,
  availableUsers = [],
}) {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("viewer");
  const available = (availableUsers || []).filter(
    (u) => !members.find((m) => m.username === u.username)
  );

  useEffect(() => {
    if (available.length && !username) setUsername(available[0].username);
  }, [available, username]);

  return (
    <div className="flex flex-wrap items-end gap-2">
      <Field label="User">
        <Select
          value={username}
          onChange={setUsername}
          options={[
            { value: "", label: "-- Select User --" },
            ...available.map((u) => ({ value: u.username, label: u.username })),
          ]}
        />
      </Field>
      <Field label="Role">
        <Select
          value={role}
          onChange={setRole}
          options={[
            { value: "admin", label: "admin" },
            { value: "manager", label: "manager" },
            { value: "engineer", label: "engineer" },
            { value: "viewer", label: "viewer" },
          ]}
        />
      </Field>
      <Button onClick={() => onAdd(username, role)} disabled={!username}>
        Add
      </Button>
    </div>
  );
}
