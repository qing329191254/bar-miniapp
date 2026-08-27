<script>
export default {
	onLaunch() {},
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
.pbody { padding: 14px 14px 88px; }
.card {
	background: #fff;
	border: 1px solid rgba(28,27,25,.12);
	border-radius: 14px;
	padding: 14px;
	margin-bottom: 12px;
}
.row { display: flex; align-items: center; gap: 8px; }
.between { display: flex; justify-content: space-between; align-items: center; }
.tiny { color: #9C9A93; font-size: 11px; }
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
	border-radius: 10px;
	padding: 10px 14px;
	background: #1C1B19;
	color: #fff;
	font-weight: 600;
	line-height: 1.2;
}
.btn.gold { background: #BA7517; color: #fff; }
.btn.ghost { background: transparent; border: 1px solid rgba(28,27,25,.24); color: #1C1B19; }
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
.chip.on { background: #1C1B19; color: #fff; border-color: #1C1B19; }
.h2 { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.empty { text-align: center; color: #9C9A93; padding: 40px 0; }
.ptabs {
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	display: flex;
	background: #fff;
	border-top: 1px solid rgba(28,27,25,.12);
	padding: 8px 0 16px;
	z-index: 20;
}
.ptab { flex: 1; text-align: center; font-size: 11px; color: #9C9A93; }
.ptab.on { color: #1C1B19; font-weight: 600; }
.ptab-i { width: 20px; height: 20px; border-radius: 6px; background: rgba(28,27,25,.12); margin: 0 auto 3px; }
.ptab.on .ptab-i { background: #1C1B19; }
.fab {
	position: fixed;
	right: 14px;
	bottom: 78px;
	width: 52px;
	height: 52px;
	border-radius: 50%;
	background: #1C1B19;
	color: #fff;
	font-size: 10px;
	line-height: 1.3;
	display: flex;
	align-items: center;
	justify-content: center;
	text-align: center;
	box-shadow: 0 4px 12px rgba(28,27,25,.25);
	z-index: 21;
}
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
	border: 1px solid rgba(28,27,25,.12);
	border-radius: 16px;
	padding: 15px 4px 13px;
	margin-bottom: 12px;
}
.kg-i { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: 11.5px; color: #6B6A65; }
.kg-i .ic {
	width: 46px; height: 46px; border-radius: 50%; color: #fff;
	display: flex; align-items: center; justify-content: center;
	font-size: 18px; font-weight: 600;
	box-shadow: 0 3px 8px rgba(28,27,25,.16);
}
.home-op {
	display: flex; align-items: center; gap: 12px;
	background: #fff; border: 1px solid rgba(28,27,25,.12);
	border-radius: 15px; padding: 13px 14px; margin-bottom: 11px;
}
.home-ic {
	width: 40px; height: 40px; border-radius: 12px; color: #fff;
	display: flex; align-items: center; justify-content: center;
	font-size: 16px; font-weight: 600; flex-shrink: 0;
}
.home-txt { flex: 1; min-width: 0; }
.ht { font-size: 14px; font-weight: 600; }
.hs { font-size: 11px; color: #6B6A65; margin-top: 2px; }
.home-arr { color: #9C9A93; font-size: 17px; }
.note {
	font-size: 11px; color: #185FA5; background: #E6F1FB;
	border-radius: 7px; padding: 7px 9px; margin-bottom: 11px; line-height: 1.6;
}
.profile-hd {
	position: relative;
	background: linear-gradient(135deg,#23201B 0%,#3A332A 55%,#57473B 100%);
	border-radius: 18px; padding: 19px 16px 17px; color: #fff; margin-bottom: 12px;
}
.ph-lg {
	width: 54px; height: 54px; border-radius: 50%; font-size: 16px;
	background: linear-gradient(135deg,#8F87E0,#D96A96); color: #fff;
	display: flex; align-items: center; justify-content: center; font-weight: 600; flex-shrink: 0;
}
.pill-w {
	display: inline-block; border-radius: 99px; padding: 1px 8px; font-size: 11px;
	background: rgba(255,255,255,.16); color: #fff;
}
.asset-card {
	background: #fff; border: 1px solid rgba(28,27,25,.12);
	border-radius: 15px; padding: 8px 4px; margin-bottom: 12px;
}
.asset-grid { display: flex; }
.asset { flex: 1; text-align: center; padding: 8px 2px; }
.ab { font-size: 16px; font-weight: 600; }
.asset text { font-size: 10.5px; color: #9C9A93; display: block; margin-top: 2px; }
.honor-grid { display: flex; gap: 11px; margin-bottom: 12px; }
.honor { flex: 1; border-radius: 15px; padding: 13px 14px 12px; color: #fff; }
.honor.g { background: linear-gradient(135deg,#8A5A14,#BA7517); }
.honor.gn { background: linear-gradient(135deg,#2F5B2A,#4E8F3E); }
.hv { font-size: 23px; font-weight: 600; margin-top: 3px; }
.hl { font-size: 10.5px; opacity: .88; margin-top: 1px; }
.seg { display: flex; background: #EDEBE4; border-radius: 12px; padding: 3px; margin-bottom: 13px; }
.seg-b { flex: 1; border: none; background: transparent; border-radius: 9px; padding: 8px 0; font-size: 13px; color: #6B6A65; }
.seg-b.on { background: #fff; color: #1C1B19; font-weight: 600; box-shadow: 0 1px 4px rgba(28,27,25,.1); }
.rk-reward { background: linear-gradient(135deg,#FDF4E3,#FAEEDA); border: 1px solid #BA7517; border-radius: 13px; padding: 12px 14px; margin-bottom: 13px; }
.rk-box { background: #fff; border: 1px solid rgba(28,27,25,.12); border-radius: 15px; padding: 6px; margin-bottom: 12px; }
.rk-row { display: flex; align-items: center; gap: 10px; padding: 10px 11px; border-radius: 11px; }
.rk-row.me { background: #E6F1FB; }
.rk-no { width: 22px; height: 22px; border-radius: 7px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #9C9A93; background: #F1EFE9; flex-shrink: 0; }
.rk-no.top { background: linear-gradient(135deg,#F6C96A,#D99A2B); color: #fff; }
.rk-mine { display: flex; align-items: center; gap: 8px; background: #fff; border: 1px solid rgba(28,27,25,.12); border-radius: 12px; padding: 10px 12px; }
.rk-tag { font-size: 11px; color: #185FA5; background: #E6F1FB; border-radius: 99px; padding: 2px 8px; }
.stodo-tabs { display: flex; flex-wrap: wrap; gap: 7px; padding: 2px 0 10px; }
.stodo-tab {
	width: calc(50% - 4px); box-sizing: border-box;
	border: 1px solid rgba(28,27,25,.12); background: #fff; color: #6B6A65;
	border-radius: 10px; padding: 8px 6px; font-size: 12.5px;
	display: flex; align-items: center; justify-content: center; gap: 5px;
}
.stodo-tab.on { background: #1C1B19; border-color: #1C1B19; color: #fff; font-weight: 600; }
.stodo-n {
	display: inline-flex; align-items: center; justify-content: center;
	min-width: 17px; height: 17px; padding: 0 4px; border-radius: 9px;
	background: #E24B4A; color: #fff; font-size: 10.5px; font-weight: 600;
}
.stodo-tab.on .stodo-n { background: #fff; color: #1C1B19; }
.stat5 { display: flex; }
.stat5 > view { flex: 1; text-align: center; }
.sb { font-size: 15px; font-weight: 600; }
.li { display: flex; align-items: center; gap: 10px; padding: 11px 0; border-bottom: 1px solid rgba(28,27,25,.12); }
.li:last-child { border-bottom: none; }
.li .gr { flex: 1; min-width: 0; }
.wiz-step { display: flex; align-items: center; gap: 5px; margin-bottom: 12px; }
.sdot {
	width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
	display: flex; align-items: center; justify-content: center;
	font-size: 11px; background: #EDEBE4; color: #9C9A93;
}
.sdot.on { background: #1C1B19; color: #fff; font-weight: 600; }
.sdot.done { background: #3B6D11; color: #fff; }
.sln { flex: 1; height: 2px; background: rgba(28,27,25,.12); }
.icell {
	width: calc(33.33% - 6px); box-sizing: border-box;
	border: 1px solid rgba(28,27,25,.12); border-radius: 10px;
	padding: 12px 4px; text-align: center; font-size: 12px; background: #fff;
}
.icell.on { border-color: #1C1B19; border-width: 2px; background: #FAF9F5; font-weight: 500; }
.icell-i { width: 26px; height: 26px; border-radius: 8px; background: #D3D1C7; margin: 0 auto 5px; }
.icell.on .icell-i { background: #1C1B19; }
.g4 { display: flex; flex-wrap: wrap; gap: 8px; }
.g4 > .icell { width: calc(25% - 6px); }
.av-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.av-pick { width: calc(25% - 8px); text-align: center; font-size: 11px; color: #6B6A65; }
.av-pick.on .av { background: #1C1B19; color: #fff; }
.cup {
	width: 26px; height: 26px; border-radius: 7px; background: #fff;
	border: 1px solid rgba(28,27,25,.24); font-size: 10px; color: #9C9A93;
	display: flex; align-items: center; justify-content: center; margin-left: 8px; flex-shrink: 0;
}
.cup.on { background: #BA7517; border-color: #BA7517; color: #fff; }
.payok { text-align: center; padding: 18px 0 6px; }
.ring {
	width: 52px; height: 52px; border-radius: 50%; background: #EAF3DE;
	border: 2px solid #3B6D11; color: #3B6D11; font-size: 24px;
	display: flex; align-items: center; justify-content: center; margin: 0 auto 10px;
}
</style>
