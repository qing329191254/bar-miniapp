/** Quick sanity check for tier-B alert diff logic (no uni runtime). */
function hasNewIds(nextIds, lastIds) {
  if (!lastIds) return false;
  return [...nextIds].some((id) => !lastIds.has(id));
}

function processAlerts(last, next) {
  const fired = [];
  const acceptIds = new Set(next.accept?.ids || []);
  const rechargeIds = new Set(next.recharge?.ids || []);
  const withdrawalIds = new Set(next.withdrawal?.ids || []);
  if (hasNewIds(acceptIds, last.accept)) fired.push("strong");
  else if (hasNewIds(rechargeIds, last.recharge)) fired.push("weak:recharge");
  else if (hasNewIds(withdrawalIds, last.withdrawal)) fired.push("weak:withdrawal");
  return fired;
}

const last = {
  accept: new Set([1]),
  recharge: new Set([10]),
  withdrawal: new Set([20]),
};

const cases = [
  { name: "new accept only", next: { accept: { ids: [1, 2] }, recharge: { ids: [10] }, withdrawal: { ids: [20] } }, expect: ["strong"] },
  { name: "new recharge only", next: { accept: { ids: [1] }, recharge: { ids: [10, 11] }, withdrawal: { ids: [20] } }, expect: ["weak:recharge"] },
  { name: "new withdrawal only", next: { accept: { ids: [1] }, recharge: { ids: [10] }, withdrawal: { ids: [20, 21] } }, expect: ["weak:withdrawal"] },
  { name: "accept+recharge same tick", next: { accept: { ids: [1, 2] }, recharge: { ids: [10, 11] }, withdrawal: { ids: [20] } }, expect: ["strong"] },
  { name: "pay only (no bucket)", next: { accept: { ids: [1] }, recharge: { ids: [10] }, withdrawal: { ids: [20] } }, expect: [] },
];

let failed = 0;
for (const c of cases) {
  const got = processAlerts(last, c.next);
  const ok = JSON.stringify(got) === JSON.stringify(c.expect);
  console.log(ok ? "PASS" : "FAIL", c.name, got);
  if (!ok) failed++;
}
process.exit(failed ? 1 : 0);
