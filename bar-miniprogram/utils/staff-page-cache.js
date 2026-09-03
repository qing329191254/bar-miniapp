/** 员工端 Tab 页缓存：redirectTo 切换会销毁页面，用内存缓存避免白屏闪烁 */
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
}
