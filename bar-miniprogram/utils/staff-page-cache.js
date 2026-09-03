/** Tab 页内存缓存：redirectTo 切换会销毁页面，缓存避免白屏闪烁 */

// --- staff ---
let mineMe = null;
let todoList = null;

export function getStaffMineCache() {
  return { me: mineMe, todo: todoList };
}

export function setStaffMineCache(me, todo) {
  mineMe = me;
  if (todo) todoList = todo;
}

export function getStaffTodoListCache() {
  return todoList;
}

export function setStaffTodoListCache(data) {
  todoList = data;
}

export function clearStaffPageCache() {
  mineMe = null;
  todoList = null;
  clearMemberPageCache();
}

// --- member (customer portal tabs) ---
let memberHome = null;
let memberRank = null;
let memberMine = null;

export function getMemberHomeCache() {
  return memberHome;
}

export function setMemberHomeCache(data) {
  memberHome = data;
}

export function getMemberRankCache() {
  return memberRank;
}

export function setMemberRankCache(data) {
  memberRank = data;
}

export function getMemberMineCache() {
  return memberMine || { me: null, champs: null, team: null };
}

export function setMemberMineCache({ me, champs, team } = {}) {
  memberMine = {
    me: me !== undefined ? me : memberMine?.me ?? null,
    champs: champs !== undefined ? champs : memberMine?.champs ?? null,
    team: team !== undefined ? team : memberMine?.team ?? null,
  };
}

export function clearMemberPageCache() {
  memberHome = null;
  memberRank = null;
  memberMine = null;
}
