from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import random
from datetime import datetime, timezone, timedelta
import json
import os
import re
import httpx

# 插件接口常量配置
RECHARGE_API_PATH = "/api/internal/award-points-by-email"

# 运势及宜忌数据源（已完全去技术化，专注于情感陪伴、校园恋爱与青春日常）
events_list = [
    ["大喊“老师来了”", "成功拯救全班正在摸鱼/玩手机的兄弟，功德无量", "老师就在你身后幽幽地看着你，气氛瞬间凝固"],
    ["食堂抢饭", "凭借风骚走位抢到最后一份糖醋排骨，全场瞩目", "跑太快一脚滑倒，在众目睽睽之下给阿姨拜了个早年"],
    ["扮演野生奥特曼", "在走廊完美展示大招姿势，被路过的校花直呼“中二”但很可爱", "刚喊出台词，教导主任突然探头，场面一度失去控制"],
    ["偷看死党手机", "抓包TA正在偷偷给喜欢的人写肉麻小作文，掌握绝对把柄", "正好看到死党在用你的丑照当表情包，友谊小船说翻就翻"],
    ["上课打瞌睡", "睡功了得，全程保持“记笔记”的僵硬姿势骗过所有人", "突然惊醒并伴随着一声惊天大呼，全班寂静，老师停下了粉笔"],
    ["请全宿舍喝奶茶", "外卖刚好有神仙大额券，四舍五入等于不要钱，狂揽全寝室父爱", "忘领优惠券，结账时直接破产，接下来三天只能蹭室友的泡面"],
    ["模仿班主任", "惟妙惟肖，连语气神态都拿捏得死死的，获得全班疯狂鼓掌", "回头发现班主任正端着保温杯，在后门窗户死亡凝视"],
    ["讲冷笑话", "全场爆笑，你就是今日的群聊/寝室相声大师", "空气瞬间安静，只有头顶的电风扇在尴尬地吱呀作响"],
    ["上厕所忘带纸", "群里求助，好兄弟三分钟内跨越半个教学楼火速送达，父爱如山", "群里没人理，甚至还被损友们截图做成了群公告"],
    ["课间操领舞", "动作极其妖娆奔放，直接成为全校名人，喜提“南区舞王”称号", "裤子质量不好当场开线，只能假装什么都没发生一路横着挪回教室"],
    # --- 校园恋爱与青春暗恋篇 ---
    ["操场散步", "并肩走在晚风里，不小心碰到的指尖都带着电", "突然偶遇班主任，吓得两人瞬间各走一边"],
    ["晚自习传纸条", "字里行间的碎碎念，全是只有你们懂的秘密", "被巡查的老师从窗户抓包，喜提“请家长”单人券"],
    ["小卖部偶遇", "为了制造“偶遇”跑了三次，刚好买到对方最喜欢的饮料", "结账时发现饭卡没钱，在对方注视下尴尬退场"],
    ["教学楼等放学", "并肩走下楼梯，夕阳把两人的影子拉得好长", "左等右等，结果对方早就从另一个楼梯口走远了"],
    ["借记事本", "字迹工整，里面还偷偷夹着一颗大白兔奶糖", "上面全是鬼画符，甚至还有上课流口水的口水渍"],
    ["课堂对视", "穿过大半个教室和无数同学，眼神撞在一起时心跳漏了一拍", "被老师误以为你想回答问题，直接叫起来背诵全文"],
    ["图书馆邻座", "阳光洒在侧脸上，连翻书的声音都变得无比温柔", "学着学着睡着了，醒来发现自己流了对方一桌子口水"],
    ["校园广播站点歌", "一首情歌把你的心意藏在广播里，全校都能听见", "名字念错了，变成了给隔壁班死对头点歌，全校都在吃瓜"],
    ["运动会送水", "在终点线拿着水等TA，跑完直接迎面抱个满怀", "送水的人太多，TA接了别人的，你手里的水瞬间沉重"],
    ["雨天撑伞", "伞明显往TA那边倾斜，自己的半边肩膀全是湿的，但也超甜", "风太大直接把伞掀翻，两个人一起在暴雨里风中凌乱"],
    ["走廊罚站", "两个人一起被赶出来，相视一笑，罚站也变成了约会", "只有你一个人在走廊，对方在教室里笑得最大声"],
    ["单车后座", "风吹起白衬衫，双手揪着TA的衣角，世界都变慢了", "路上链条突然断了，两个人不得不苦哈哈地推着车走回学校"],

    # --- 深度情感陪伴与心理互动篇 ---
    ["私聊喜欢的人", "消息秒回，聊到深夜", "“对方开启了好友验证”"],
    ["吃醋", "傲娇一下反而让对方更在乎你", "气到原地爆炸，对方还以为你在开玩笑"],
    ["讨要安全感", "得到一长串超级温柔的连发气泡安抚", "对方回了个“？”并让你多喝热水"],
    ["假装高冷", "欲擒故纵，对方立刻紧张地粘过来", "直接把天聊死，进入漫长冷战"],
    ["语音通话", "声音超温柔，耳机党反复去世", "全程沉默，只有尴尬的呼吸声和背景音"],
    ["深夜网聊", "两情若是久长时，又岂在朝朝暮暮", "困到手机砸脸，还发了一串乱码"],
    ["翻看历史记录", "字里行间全是糖，甜到掉牙", "发现自己以前像个绝世舔狗"],
    ["秒回消息", "体现你满满的偏爱与重视", "显得你很闲，而且对方过了半小时才回"],
    ["分享日常", "事事有回应，件件有着落", "对方回了个“哦”，热情瞬间被浇灭"],
    ["深夜emo", "获得暖心 AI 或好友的彻夜陪伴", "第二天眼睛肿得像核桃，还要早起上班"],
    ["暗示表白", "心有灵犀，对方顺杆爬直接官宣", "对方完美避开正确答案，铁直男无疑"],
    ["主动贴贴", "抱团取暖，安全感瞬间拉满", "被嫌弃太热并被无情推开"],
    ["查岗", "坦坦荡荡，信任感更进一步", "发现对方的小秘密，当场心碎成渣"],
    ["发委屈表情包", "对方心软一塌糊涂，疯狂摸头安慰", "被对方收藏，并回了一个更搞笑的嘲讽表情"],
    ["胡思乱想", "其实对方真的很爱你，别瞎猜啦", "越想越气，成功把自己气哭"],
    ["温柔对视", "一眼万年，空气开始拉丝", "眼神呆滞，看起来像在看傻子"],
    ["诉说心事", "把脆弱留给对的人，会得到加倍的温柔", "人类的欢喜并不相通，对方觉得你太矫情"],
    ["约会出行", "精心打扮，每一秒都是偶像剧情节", "临出门开始下暴雨，发型瞬间塌掉"],
    ["准备惊喜", "对方感动到眼眶泛红，RP爆棚", "用力过猛变成惊吓，甚至被怀疑干了坏事"],
    ["发朋友圈秀恩爱", "收获全群的祝福与柠檬酸", "仅三天可见，过几天就悄悄删了"],
    ["连发消息", "情绪价值拉满，小作文也有人耐心看完", "被视为轰炸机，触发对方的免疫系统"],
    ["冷战", "给彼此一个冷静的空间", "冷着冷着，关系就真的凉透了"],
    ["听情歌", "每一句歌词写的都是你们的故事", "越听越网抑云，开始怀疑人生"],
    ["换情侣头像", "低调炫耀，占有欲得到极大满足", "被长辈误认为是违规账号或者微商"],
    ["睡前道晚安", "最后一个跟你说话的人，今晚一定有好梦", "刚说完晚安，转头在游戏里或者B站偶遇"],
    ["偷偷吃醋", "对方发现后会觉得你超级可爱，疯狂哄你", "憋在心里内伤，最后变成阴阳怪气"],
    ["情绪宣泄", "痛痛快快哭一场，积压的委屈全部释放", "憋成闷葫芦，对亲近的人乱发脾气"],
    ["给对方挑衣服", "审美在线，穿出去惊艳全场", "买到死亡芭比粉，被压在箱底落灰"],
    ["深夜分享网易云", "正好撞上对方此时的心情，灵魂共鸣", "对方没开蓝牙，外放出来吵醒了舍友"],
    ["要抱抱", "跨越距离的拥抱，什么烦恼都没了", "张开双臂迎接你的是无情的冷空气"]
]
# 🌟 升级版运势配置：(运势名, 随机权重, (点数下限, 点数上限), 趣味签文)
fortune_levels = [
    ("大凶", 1, (10, 15), "代码全是Bug，连AI都嫌弃。别怕，送你点数回去重构人生！"),
    ("凶", 3, (12, 18), "感觉今天总有刁民想害朕？拿上这笔巨款去买杯奶茶续命。"),
    ("中平", 4, (15, 22), "波澜不惊的一天，稳扎稳打才是王道。点数请收好~"),
    ("吉", 3, (20, 28), "空气里都是甜的，今天写代码指不定能一气痕成！"),
    ("小吉", 3, (20, 28), "生活中总有小惊喜在等你，比如现在突然多出来的点数。"),
    ("中吉", 2, (22, 35), "欧气正在凝聚，今天你的代码运行成功率高达 99%！"),
    ("大吉", 1, (25, 50), "哇！金色传说！心想事成，今天你就是全群最靓的仔！")
]

@register("astrbot_plugin_dailyacmfortune_zangxingai", "Dayanshifu & Zangxin", "二改洛谷运势插件：打卡自动充值点数且限一日一次", "1.2.0")
class DailyAcmFortune(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.data_dir = "data/dailyacmfortune"
        self.record_file = os.path.join(self.data_dir, "daily_checkins.json")
        os.makedirs(self.data_dir, exist_ok=True)

        # 默认回退值配置，若在 Github 仓库上可将 secret key 修改为默认防扫描占位符
        self.api_base_url = "http://127.0.0.1:8000"
        self.plugin_recharge_key = "test"

        # 直接使用 AstrBot 官方推荐注入的配置，优雅又防泄漏
        if config:
            if "api_base_url" in config and config["api_base_url"]:
                self.api_base_url = config["api_base_url"].strip()
            if "plugin_recharge_key" in config and config["plugin_recharge_key"]:
                self.plugin_recharge_key = config["plugin_recharge_key"].strip()

    def _load_records(self) -> dict:
        if os.path.exists(self.record_file):
            try:
                with open(self.record_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[ACM打卡] 读取记录文件失败: {e}")
        return {}

    def _save_records(self, records: dict):
        try:
            with open(self.record_file, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[ACM打卡] 写入记录文件失败: {e}")

    def _clean_old_records(self, records: dict, today_str: str) -> dict:
        return {today_str: records.get(today_str, {"user_ids": [], "emails": []})}

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def daily_checkin(self, event: AstrMessageEvent):
        message_str = event.message_str.strip()
        match = re.match(r"^(?:/|!)?打卡\s*([\w\.-]+@[\w\.-]+\.\w+)$", message_str, re.IGNORECASE)
        if not match:
            return

        email = match.group(1).strip()
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name() or "少侠"

        tz_utc_8 = timezone(timedelta(hours=8))
        today_str = datetime.now(tz_utc_8).strftime("%Y-%m-%d")
        
        # 1. 限额校验
        records = self._load_records()
        records = self._clean_old_records(records, today_str)
        today_data = records[today_str]

        if sender_id in today_data["user_ids"]:
            yield event.plain_result(f"⚠️ {sender_name}，您今天已经打过卡了，一天只能打卡一次哦！")
            return
        
        if email in today_data["emails"]:
            yield event.plain_result(f"⚠️ 邮箱 {email} 今天已经打过卡并获得过充值了，不可重复打卡！")
            return

        # 2. 运势生成与随机数种子锚定 (防止时序影响，用局部临时 Random 实例代替全局 seed)
        seed_str = f"{today_str}_{sender_id}"
        local_rand = random.Random(seed_str)

        # 展平权重抽取基础运势
        fortune_pool = []
        for item in fortune_levels:
            # item 格式: (name, weight, pts_range, text)
            fortune_pool.extend([item] * item[1])
        selected_fortune = local_rand.choice(fortune_pool)
        
        fortune_name = selected_fortune[0]
        pts_range = selected_fortune[2]
        flavor_text = selected_fortune[3]

        # 🌟 趣味随机：在这个人专属的种子下计算随机点数
        points = local_rand.randint(pts_range[0], pts_range[1])

        # 👑 特殊机制：大吉有 20% 的几率暴击翻倍
        if fortune_name == "大吉" and local_rand.random() < 0.2:
            points *= 2
            fortune_name = "👑 大吉 (触发强运点数翻倍!)"

        # 强制单次打卡点数最大不超过 50 点
        points = min(points, 50)

        # 抽取宜/忌事项
        shuffled_events = list(events_list)
        local_rand.shuffle(shuffled_events)
        yi_list = shuffled_events[:2]
        ji_list = shuffled_events[2:4]

        # 3. 向后端发起充值请求
        # 校验是否使用了默认的未配置占位符
        if not self.api_base_url or "[IP_ADDRESS]" in self.api_base_url or self.api_base_url.strip() in ["http://", "https://"]:
            yield event.plain_result(
                "⚠️ 充值失败：打卡插件的“后端服务地址”未正确配置！\n"
                "请登录 AstrBot 可视化管理面板进入插件设置，将“后端服务地址”修改为您真实的后端服务器 IP 及其端口（例如 http://127.0.0.1:8000）。"
            )
            return

        recharge_url = f"{self.api_base_url.rstrip('/')}{RECHARGE_API_PATH}"
        payload = {
            "email": email,
            "points": points,
            "secret_key": self.plugin_recharge_key
        }

        yield event.plain_result(f"🔄 正在为您的账户 {email} 处理打卡与运势结算...")
        
        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                res = await client.post(recharge_url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("success") is True:
                        # 充值成功后再行计入本地记录
                        today_data["user_ids"].append(sender_id)
                        today_data["emails"].append(email)
                        self._save_records(records)

                        # 构建带有趣味文案的精美返回排版
                        response_text = (
                            f"🔮 【葬心 AI · ACM 每日运势】 🔮\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"👤 签到用户: {sender_name}\n"
                            f"📅 今日日期: {today_str}\n"
                            f"✨ 今日运势: 【{fortune_name}】\n"
                            f"💬 运势批注: {flavor_text}\n"
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"💰 签到奖励: 自动为您充值 {points} 个普通点数！\n"
                            f"📧 充值账户: {email}\n"
                            f"¼ [状态]: 点数已即时入账！\n\n"
                            f"👍 宜:\n"
                            f"  - {yi_list[0][0]} ({yi_list[0][1]})\n"
                            f"  - {yi_list[1][0]} ({yi_list[1][1]})\n"
                            f"👎 忌:\n"
                            f"  - {ji_list[0][0]} ({ji_list[0][2]})\n"
                            f"  - {ji_list[1][0]} ({ji_list[1][2]})"
                        )
                        yield event.plain_result(response_text)
                    else:
                        error_detail = data.get("error", "充值未成功，请检查邮箱是否在系统注册。")
                        yield event.plain_result(f"❌ 打卡失败：{error_detail}\n未扣除您的本日打卡限额。")
                else:
                    yield event.plain_result(f"❌ 充值服务响应异常 (HTTP {res.status_code})，请联系管理员检查后端。")
        except Exception as e:
            logger.error(f"[ACM打卡] 连接充值服务出错: {e}")
            yield event.plain_result("❌ 打卡失败，连接充值服务超时或出错，请稍后再试。")
