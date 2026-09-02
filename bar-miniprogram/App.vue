<script>
import { startStaffReminder, stopStaffReminder } from "@/utils/staff-reminder";

export default {
	onLaunch() {
		if (typeof wx !== "undefined" && wx.cloud) {
			wx.cloud.init({ env: "prod-d2gc6jcwy846bd613" });
		}
		const u = uni.getStorageSync("wanka_user");
		const t = uni.getStorageSync("wanka_token");
		if (!u || !u.role || !t) return;
		uni.reLaunch({
			url: u.role === "CUSTOMER" ? "/pages/c/home" : "/pages/s/todo",
		});
	},
	onShow() {
		startStaffReminder();
	},
	onHide() {
		stopStaffReminder();
	},
};
</script>

<style>
page {
	background: #F5F4F0;
	color: #1C1B19;
	font-size: 14px;
	line-height: 1.55;
}
button {
	padding: 0;
	margin: 0;
	background: none;
	font-size: 14px;
	line-height: 1.55;
	color: inherit;
}
button::after { border: none; }
.pbody { padding: 14px 14px calc(92px + env(safe-area-inset-bottom)); }
.foot-btn { margin-bottom: 4px; }
.card {
	background: #fff;
	border: 1px solid rgba(28,27,25,.1);
	border-radius: 16px;
	padding: 14px;
	margin-bottom: 12px;
	box-shadow: 0 1px 3px rgba(28,27,25,.04);
}
.card.flat { box-shadow: none; }
.row { display: flex; align-items: center; gap: 8px; }
.between { display: flex; justify-content: space-between; align-items: center; }
.tiny { color: #9C9A93; font-size: 11px; }
.number-display {
	font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
	font-variant-numeric: tabular-nums;
	font-feature-settings: "tnum";
	font-weight: 600;
	letter-spacing: -.5px;
}
.gold { color: #BA7517; }
.pill {
	display: inline-block;
	border-radius: 99px;
	padding: 1px 8px;
	font-size: 11px;
	background: #FAEEDA;
	color: #BA7517;
}
.btn {
	border: none;
	border-radius: 12px;
	padding: 10px 14px;
	background: #1C1B19;
	color: #fff;
	font-weight: 600;
	line-height: 1.2;
}
.btn.gold { background: linear-gradient(135deg,#C8862A,#E8B45A); color: #fff; }
.btn.grad-dark { background: linear-gradient(135deg,#23201B,#4A4038); color: #fff; }
.btn.ghost { background: transparent; border: 1px solid rgba(28,27,25,.2); color: #1C1B19; }
.btn.danger { background: #FCEBEB; color: #A32D2D; }
.btn.block { width: 100%; }
.btn + .btn { margin-left: 8px; }
.row > .btn + .btn,
.g2 > .btn + .btn,
.g3 > .btn + .btn { margin-left: 0; }
.g2 { display: flex; flex-wrap: wrap; gap: 10px; }
.g2 > .card, .g2 > .btn { width: calc(50% - 5px); box-sizing: border-box; }
.g3 { display: flex; gap: 8px; }
.g3 > .btn { flex: 1; font-size: 12px; padding: 12px 2px; }
.err { color: #A32D2D; font-size: 12px; margin: 8px 0; }
.acct {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 12px;
	border: 1px solid rgba(28,27,25,.12);
	border-radius: 12px;
	background: #fff;
	margin-bottom: 8px;
	width: 100%;
	text-align: left;
}
.av {
	width: 36px;
	height: 36px;
	border-radius: 50%;
	background: #FAEEDA;
	color: #BA7517;
	display: flex;
	align-items: center;
	justify-content: center;
	font-weight: 700;
	flex-shrink: 0;
	font-size: 12px;
}
.catbar { display: flex; gap: 8px; white-space: nowrap; padding-bottom: 8px; margin-bottom: 8px; }
.chip {
	border: 1px solid rgba(28,27,25,.12);
	background: #fff;
	border-radius: 99px;
	padding: 6px 12px;
	color: #6B6A65;
	font-size: 13px;
}
.chip.on { background: linear-gradient(135deg,#1C1B19,#3A3530); color: #fff; border-color: transparent; box-shadow: 0 2px 8px rgba(28,27,25,.15); }
.h2 { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.empty { text-align: center; color: #9C9A93; padding: 40px 0; }
.ptab { flex: 1; text-align: center; font-size: 11px; color: #9C9A93; display: flex; flex-direction: column; align-items: center; }
.ptab.on { color: #1C1B19; font-weight: 600; }
.ptab-i { width: 22px; height: 22px; margin: 0 auto 3px; display: block; }
.field {
	width: 100%;
	padding: 8px;
	border-radius: 8px;
	border: 1px solid rgba(28,27,25,.12);
	background: #fff;
	box-sizing: border-box;
	margin-bottom: 8px;
}
.home-b {
	position: relative;
	border-radius: 16px;
	overflow: hidden;
	height: 150px;
	margin-bottom: 14px;
	box-shadow: 0 4px 14px rgba(28,27,25,.12);
	background-size: cover;
	background-position: center;
}
.home-b.has-img:after {
	content: "";
	position: absolute;
	inset: 0;
	background: linear-gradient(180deg, rgba(0,0,0,.08), rgba(0,0,0,.38));
}
.home-b.empty-b {
	background: #F5F4F0;
	border: 1px dashed rgba(28,27,25,.24);
	box-shadow: none;
	display: flex;
	align-items: center;
	justify-content: center;
}
.home-b-in { position: absolute; left: 18px; top: 32px; color: #fff; z-index: 1; }
.home-bt { font-size: 19px; letter-spacing: 2px; font-weight: 600; }
.home-bs { font-size: 11px; opacity: .78; margin-top: 7px; letter-spacing: 1px; }
.home-b-page {
	position: absolute; right: 12px; bottom: 11px;
	background: rgba(0,0,0,.42); color: #fff; font-size: 11px;
	border-radius: 20px; padding: 3px 10px; z-index: 1;
}
.home-kg {
	display: flex;
	background: #fff;
	border: 1px solid rgba(28,27,25,.1);
	border-radius: 18px;
	padding: 16px 6px 14px;
	margin-bottom: 12px;
	box-shadow: 0 2px 8px rgba(28,27,25,.05);
}
.kg-i { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 7px; font-size: 11.5px; color: #6B6A65; font-weight: 500; }
.home-op {
	display: flex; align-items: center; gap: 12px;
	background: #fff; border: 1px solid rgba(28,27,25,.1);
	border-radius: 16px; padding: 13px 14px; margin-bottom: 11px;
	box-shadow: 0 1px 4px rgba(28,27,25,.04);
}
.home-op:active { opacity: .88; }
.home-txt { flex: 1; min-width: 0; }
.ht { font-size: 14px; font-weight: 600; }
.hs { font-size: 11px; color: #6B6A65; margin-top: 2px; }
.chev { width: 18px; height: 18px; flex-shrink: 0; opacity: .55; }
.menu-li { display: flex; align-items: center; gap: 11px; padding: 12px 0; border-bottom: 1px solid rgba(28,27,25,.08); }
.menu-li:last-child { border-bottom: none; }
.menu-li .gr { flex: 1; min-width: 0; }
.menu-title { font-weight: 500; font-size: 14px; }
.menu-sub { font-size: 11px; color: #9C9A93; margin-top: 2px; line-height: 1.45; }
.asset-card {
	background: #fff; border: 1px solid rgba(28,27,25,.1);
	border-radius: 16px; padding: 12px 8px 10px; margin-bottom: 12px;
	box-shadow: 0 2px 8px rgba(28,27,25,.05);
}
.asset-grid {
	display: grid;
	grid-template-columns: repeat(4, 1fr);
	align-items: start;
}
.asset {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: flex-start;
	min-width: 0;
	padding: 2px 4px;
	text-align: center;
}
.asset:not(:last-child) {
	border-right: 1px solid rgba(28,27,25,.06);
}
.asset-ic-wrap {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 100%;
	margin-bottom: 6px;
}
.asset-ic-wrap .app-icon {
	box-shadow: 0 2px 6px rgba(28,27,25,.1);
}
.ab {
	font-size: 15px;
	font-weight: 600;
	line-height: 1.25;
	max-width: 100%;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.asset-val-sm { font-size: 13px; }
.asset label, .asset .asset-label {
	font-size: 10.5px;
	color: #9C9A93;
	margin-top: 3px;
	line-height: 1.2;
}
.note {
	font-size: 11px; color: #185FA5; background: #E6F1FB;
	border-radius: 7px; padding: 7px 9px; margin-bottom: 11px; line-height: 1.6;
}
.profile-hd {
	position: relative;
	background: linear-gradient(135deg,#1E1A16 0%,#3D342C 48%,#5C4A3A 100%);
	border-radius: 20px; padding: 19px 16px 17px; color: #fff; margin-bottom: 12px;
	box-shadow: 0 6px 20px rgba(35,28,20,.22);
}
.staff-hd {
	background: linear-gradient(135deg,#141D2B 0%,#243B5C 52%,#3A5F8C 100%);
	border-radius: 18px; padding: 16px; color: #fff; margin-bottom: 12px;
	box-shadow: 0 6px 18px rgba(20,30,50,.2);
}
.staff-hd .pill-w { background: rgba(255,255,255,.14); color: rgba(255,255,255,.92); }
.ph-lg {
	width: 54px; height: 54px; border-radius: 50%; font-size: 16px;
	background: linear-gradient(135deg,#8F87E0,#D96A96); color: #fff;
	display: flex; align-items: center; justify-content: center; font-weight: 600; flex-shrink: 0;
}
.pill-w {
	display: inline-block; border-radius: 99px; padding: 2px 8px; font-size: 11px; line-height: 1.35;
	background: rgba(255,255,255,.16); color: #fff; white-space: nowrap;
}
.honor-grid { display: flex; gap: 11px; margin-bottom: 12px; }
.honor { flex: 1; border-radius: 16px; padding: 13px 14px 12px; color: #fff; box-shadow: 0 4px 14px rgba(28,27,25,.12); }
.honor.g { background: linear-gradient(145deg,#7A5010,#D4A035); }
.honor.gn { background: linear-gradient(145deg,#2F5B2A,#5FAF52); }
.honor-hd { display: flex; align-items: center; gap: 6px; font-size: 12px; opacity: .92; }
.honor-ic { font-size: 14px; line-height: 1; }
.hv { font-size: 23px; font-weight: 600; margin-top: 3px; }
.hl { font-size: 10.5px; opacity: .88; margin-top: 1px; line-height: 1.45; }
.seg { display: flex; background: #EDEBE4; border-radius: 14px; padding: 4px; margin-bottom: 13px; }
.seg-b { flex: 1; border: none; background: transparent; border-radius: 10px; padding: 9px 0; font-size: 13px; color: #6B6A65; }
.seg-b.on { background: linear-gradient(135deg,#fff,#FAF9F5); color: #1C1B19; font-weight: 600; box-shadow: 0 2px 6px rgba(28,27,25,.1); }
.rk-reward { background: linear-gradient(135deg,#FDF4E3,#FAEEDA); border: 1px solid rgba(186,117,23,.35); border-radius: 14px; padding: 12px 14px; margin-bottom: 13px; }
.rk-box { background: #fff; border: 1px solid rgba(28,27,25,.1); border-radius: 16px; padding: 6px; margin-bottom: 12px; box-shadow: 0 1px 4px rgba(28,27,25,.04); }
.rk-row { display: flex; align-items: center; gap: 10px; padding: 10px 11px; border-radius: 12px; }
.rk-row.me { background: linear-gradient(90deg,#E6F1FB,#F0F7FD); }
.rk-no { width: 24px; height: 24px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #9C9A93; background: #F1EFE9; flex-shrink: 0; }
.rk-no.top { background: linear-gradient(135deg,#F6C96A,#D99A2B); color: #fff; box-shadow: 0 2px 6px rgba(186,117,23,.25); }
.stodo-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 2px 0 10px; }
.stodo-tab {
	box-sizing: border-box;
	border: 1px solid rgba(28,27,25,.1); background: #fff; color: #6B6A65;
	border-radius: 12px; padding: 10px 10px; font-size: 12.5px;
	display: flex; align-items: center; gap: 8px;
	box-shadow: 0 1px 3px rgba(28,27,25,.04);
}
.stodo-tab.on { background: linear-gradient(135deg,#1C1B19,#3A3530); border-color: transparent; color: #fff; font-weight: 600; box-shadow: 0 4px 12px rgba(28,27,25,.18); }
.stodo-tab-ic { flex-shrink: 0; opacity: .95; }
.stodo-tab.on .stodo-tab-ic { opacity: 1; }
.stodo-n {
	display: inline-flex; align-items: center; justify-content: center;
	min-width: 17px; height: 17px; padding: 0 5px; border-radius: 9px;
	background: #E24B4A; color: #fff; font-size: 10.5px; font-weight: 600;
	flex-shrink: 0;
}
.stodo-tab.on .stodo-n { background: #fff; color: #1C1B19; }
.rk-mine { display: flex; align-items: center; gap: 8px; background: #fff; border: 1px solid rgba(28,27,25,.1); border-radius: 14px; padding: 11px 12px; box-shadow: 0 1px 4px rgba(28,27,25,.04); }
.rk-tag { font-size: 11px; color: #185FA5; background: linear-gradient(135deg,#E6F1FB,#D8EBFA); border-radius: 99px; padding: 3px 9px; font-weight: 500; }
.stat5 { display: flex; }
.stat5 > view { flex: 1; text-align: center; }
.sb { font-size: 15px; font-weight: 600; }
.job-stat { display: flex; align-items: center; gap: 11px; padding: 11px 0; border-bottom: 1px solid rgba(28,27,25,.08); }
.job-stat:last-child { border-bottom: none; }
.job-stat .gr { flex: 1; min-width: 0; }
.ptabs {
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	display: flex;
	background: rgba(255,255,255,.96);
	border-top: 1px solid rgba(28,27,25,.08);
	padding: 6px 0 calc(12px + env(safe-area-inset-bottom));
	z-index: 20;
	box-shadow: 0 -4px 16px rgba(28,27,25,.06);
	backdrop-filter: blur(8px);
}
.fab {
	position: fixed;
	right: 14px;
	bottom: calc(88px + env(safe-area-inset-bottom));
	width: 56px;
	height: 56px;
	border-radius: 50%;
	background: linear-gradient(145deg,#1A2332,#3D5F8C);
	color: #fff;
	font-size: 10px;
	line-height: 1.25;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	box-shadow: 0 6px 18px rgba(26,35,50,.35);
	z-index: 21;
}
.fab:active { transform: scale(.96); }
.ring {
	width: 56px; height: 56px; border-radius: 50%;
	background: linear-gradient(135deg,#EAF3DE,#D4EAC0);
	border: none; color: #3B6D11; font-size: 26px;
	display: flex; align-items: center; justify-content: center; margin: 0 auto 10px;
	box-shadow: 0 4px 14px rgba(59,109,17,.15);
}
.payok { text-align: center; padding: 18px 0 6px; }
.li { display: flex; align-items: center; gap: 10px; padding: 11px 0; border-bottom: 1px solid rgba(28,27,25,.08); }
.li:last-child { border-bottom: none; }
.li .gr { flex: 1; min-width: 0; }
.wiz-step { display: flex; align-items: center; gap: 5px; margin-bottom: 12px; }
.sdot {
	width: 24px; height: 24px; border-radius: 50%; flex-shrink: 0;
	display: flex; align-items: center; justify-content: center;
	font-size: 11px; background: #EDEBE4; color: #9C9A93;
}
.sdot.on { background: linear-gradient(135deg,#1C1B19,#4A4540); color: #fff; font-weight: 600; box-shadow: 0 2px 6px rgba(28,27,25,.2); }
.sdot.done { background: linear-gradient(135deg,#3B6D11,#6FAF52); color: #fff; }
.sln { flex: 1; height: 2px; background: rgba(28,27,25,.1); border-radius: 1px; }
.icell {
	width: calc(33.33% - 6px); box-sizing: border-box;
	border: 1px solid rgba(28,27,25,.1); border-radius: 12px;
	padding: 12px 4px; text-align: center; font-size: 12px; background: #fff;
}
.icell.on { border-color: #1C1B19; border-width: 2px; background: linear-gradient(180deg,#FAF9F5,#fff); font-weight: 500; box-shadow: 0 2px 8px rgba(28,27,25,.06); }
.icell-i { width: 28px; height: 28px; border-radius: 9px; background: linear-gradient(135deg,#D3D1C7,#E8E6E0); margin: 0 auto 5px; }
.icell.on .icell-i { background: linear-gradient(135deg,#1C1B19,#4A4540); }
.g4 { display: flex; flex-wrap: wrap; gap: 8px; }
.g4 > .icell { width: calc(25% - 6px); }
.av-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.av-pick { width: calc(25% - 8px); text-align: center; font-size: 11px; color: #6B6A65; }
.av-pick.on .av { background: linear-gradient(135deg,#1C1B19,#4A4540); color: #fff; }
.cup {
	width: 26px; height: 26px; border-radius: 8px; background: #fff;
	border: 1px solid rgba(28,27,25,.2); font-size: 10px; color: #9C9A93;
	display: flex; align-items: center; justify-content: center; margin-left: 8px; flex-shrink: 0;
}
.cup.on { background: linear-gradient(135deg,#BA7517,#E8B45A); border-color: transparent; color: #fff; }
</style>
