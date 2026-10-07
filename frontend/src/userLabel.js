export function userLabel(person) {
  const name = String(person?.name || "").trim();
  return name || person?.username || "";
}
