/** 微信小程序分享：发给朋友 / 朋友圈 */

export const SHARE_TITLE = "玩咖桌游酒吧";
export const SHARE_DESC = "点单 · 充值 · 积分 · 桌游对局";
/** 分享落地走 boot，由会话决定进登录 / 会员 / 选端 */
export const SHARE_PATH = "/pages/boot/boot";
export const SHARE_IMAGE = "/static/share-cover.png";

export function shareAppMessage() {
  return {
    title: SHARE_TITLE,
    path: SHARE_PATH,
    imageUrl: SHARE_IMAGE,
  };
}

export function shareTimeline() {
  return {
    title: SHARE_TITLE,
    query: "",
    imageUrl: SHARE_IMAGE,
  };
}

/** Vue mixin：所有页面右上角菜单可转发 / 分享朋友圈 */
export const shareMixin = {
  onShareAppMessage() {
    return shareAppMessage();
  },
  onShareTimeline() {
    return shareTimeline();
  },
};
