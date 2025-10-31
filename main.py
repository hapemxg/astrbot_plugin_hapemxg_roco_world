# 引入 AstrBot 插件开发所需的核心库
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# 引入 Python 内置的数学计算和正则表达式库
import math
import re

# @register 装饰器用于注册插件信息
# 分别是：插件ID, 作者, 插件描述, 插件版本号
@register("calculator", "hapemxg", "洛克王国数值计算器", "1.4.2")
class CalculatorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # --- 将固定的游戏参数作为类属性，方便管理 ---
        self.LEVEL = 60
        self.EFFORT_VALUE = 50
        self.INDIVIDUAL_VALUE = 60 # 满个体值
        self.PERSONALITY_MULTIPLIER = 1.2

    # --- 内部核心计算方法 ---
    
    def _parse_stat_input(self, input_str: str) -> tuple[int, bool, int]:
        clean_str = input_str.replace("我方", "").replace("对方", "").strip()
        base_race_match = re.match(r"^\s*(\d+)", clean_str)
        if not base_race_match: raise ValueError("格式错误，必须以种族值数字开头。")
        base_race_value = int(base_race_match.group(1))
        has_personality = "性格" in clean_str
        final_iv = 0
        iv_match = re.search(r"个体(\d+)", clean_str)
        if iv_match:
            iv_num = int(iv_match.group(1))
            allowed_points = {7, 8, 9, 10}
            allowed_totals = {42, 48, 54, 60}
            if iv_num not in allowed_points and iv_num not in allowed_totals:
                raise ValueError(f"个体值不合法：'{iv_num}'。请输入点数(7-10)或总值(42,48,54,60)。")
            final_iv = iv_num * 6 if iv_num in allowed_points else iv_num
        elif "个体" in clean_str:
            final_iv = self.INDIVIDUAL_VALUE
        return (base_race_value, has_personality, final_iv)

    def _parse_quick_mode_attacker(self, input_str: str) -> tuple[int, bool, int]:
        base_race_match = re.match(r'^(\d+)', input_str)
        if not base_race_match:
            raise ValueError(f"快速模式格式错误: '{input_str}' 必须以数字开头。")
        
        base_race = int(base_race_match.group(1))
        suffixes = input_str[len(base_race_match.group(1)):]

        if suffixes.count('g') > 1 or suffixes.count('x') > 1:
            raise ValueError(f"快速模式格式错误: '{input_str}' 包含重复的 'g' 或 'x' 后缀。")
        
        temp_suffixes = suffixes.replace('x', '')
        g_match_validation = re.search(r'g(\d+)?', temp_suffixes)
        if g_match_validation:
            temp_suffixes = temp_suffixes.replace(g_match_validation.group(0), '')
        if temp_suffixes:
            raise ValueError(f"快速模式格式错误: '{input_str}' 包含无法识别的后缀 '{temp_suffixes}'。")

        has_pers = 'x' not in suffixes
        final_iv = self.INDIVIDUAL_VALUE
        g_match = re.search(r'g(\d+)?', suffixes)
        if g_match:
            iv_num_str = g_match.group(1)
            if iv_num_str:
                iv_points = int(iv_num_str)
                if not (7 <= iv_points <= 10):
                    raise ValueError(f"快速模式个体值点数 '{iv_points}' 不合法，必须为 7-10。")
                final_iv = iv_points * 6
            else:
                final_iv = 0
        return base_race, has_pers, final_iv
    
    def _get_main_reverse_help_text(self) -> str:
        """/反推 指令的帮助文本"""
        return (
            "--- 反推指令帮助 ---\n\n"
            "本插件提供三种反推计算功能：\n\n"
            "> /反推防御 : 根据你造成的伤害，反推对方的防御能力。\n"
            "> /反推攻击 : 根据你受到的伤害，反推对方的攻击能力。\n"
            "> /精力反推 : 根据伤害和掉血百分比，反推对方的精力。\n\n"
            "要查看具体指令的详细用法，请在指令后加上“帮助”，例如：\n"
            "/反推防御 帮助"
        )

    def _get_reverse_help_text(self) -> str:
        """防御反推指令的帮助文本"""
        return (
            "--- 伤害反推(防御)指令帮助 ---\n\n"
            "该指令用于根据你造成的伤害，反推对方的防御能力养成。\n\n"
            "--- 快速模式 ---\n"
            "格式: /反推防御 [我方攻击信息] [对方防御种族] [威力] [伤害]\n"
            "我方信息代码: g(个体), x(性格)\n"
            "示例: /反推防御 186xg8 80 75 130\n\n"
            "--- 智能模式 ----\n"
            "说明: 参数顺序随意，通过关键字自动识别。\n"
            "示例: /反推防御 我方186+性格 对方80 威力75 130伤害"
        )

    def _get_reverse_attack_help_text(self) -> str:
        return (
            "--- 伤害反推(攻击)指令帮助 ---\n\n"
            "该指令用于根据你受到的伤害，反推对方的攻击能力养成。\n\n"
            "--- 快速模式 ---\n"
            "格式: /反推攻击 [我方防御信息] [对方攻击种族] [威力] [伤害]\n"
            "示例: /反推攻击 100xg8 186 75 130\n\n"
            "--- 智能模式 ----\n"
            "说明: 参数顺序随意，通过关键字自动识别。\n"
            "示例: /反推攻击 我方100+性格 对方186 威力75 130伤害"
        )

    def _get_reverse_hp_help_text(self) -> str:
        """精力反推指令的帮助文本"""
        return (
            "--- 精力反推指令帮助 ---\n\n"
            "根据造成的伤害和对方掉血百分比，反推其精力养成情况。\n\n"
            "--- 格式 ---\n"
            "/精力反推 [对方精力种族] [掉血百分比] [伤害值]\n\n"
            "--- 快速模式 (无关键字) ---\n"
            "说明: 按顺序输入3个数字即可。\n"
            "示例: /精力反推 128 20 102\n"
            " (对方128精力种族, 掉血20%, 伤害102)\n\n"
            "--- 智能模式 (有关键字) ---\n"
            "说明: 顺序随意，通过关键字识别，更清晰。\n"
            "关键字: `对方`, `掉血`, `伤害` (`%`可选)\n"
            "示例:\n"

            "  /精力反推 对方128 掉血20% 伤害102\n"
            "  /精力反推 伤害102 对方128 掉血20"
        )

    def _calculate_stat(self, base_race_value: int, personality: bool, individual_value: int) -> int:
        """计算除精力外的五维属性（物攻、魔攻、物防、魔防、速度）"""
        personality_to_use = self.PERSONALITY_MULTIPLIER if personality else 1.0
        l_coefficient = (base_race_value + individual_value / 2) / 100
        initial_stat = l_coefficient * (self.LEVEL + 50) + 10
        final_stat = initial_stat * personality_to_use + self.EFFORT_VALUE
        return math.ceil(final_stat)

    def _calculate_hp(self, base_race_value: int, personality: bool, individual_value: int) -> int:
        """根据特殊公式计算精力（HP）属性"""
        personality_to_use = self.PERSONALITY_MULTIPLIER if personality else 1.0
        l_coefficient = (base_race_value + individual_value / 2) / 100
        initial_hp = (2 * l_coefficient + 1) * self.LEVEL + 50 * l_coefficient + 10
        final_hp = initial_hp * personality_to_use + self.EFFORT_VALUE
        return math.ceil(final_hp)

    def _calculate_damage(self, attack: int, defense: int, skill_power: int) -> int:
        if defense <= 0: return 9999
        damage = (attack / defense) * 0.9 * skill_power
        return math.floor(damage)

    # --- 指令组：计算器 ---

    @filter.command_group("计算器")
    def calculator(self):
        """洛克王国数值计算器指令组"""
        pass

    @calculator.command("精力计算")
    async def hp_calculator(self, event: AstrMessageEvent):
        """计算最终的精力（HP）值"""
        try:
            command_parts = event.message_str.split()
            if len(command_parts) < 3:
                 yield event.plain_result("参数不能为空。用法: /计算器 精力计算 150+性格+个体10")
                 return
            params = " ".join(command_parts[2:])

            base_race, has_pers, final_iv = self._parse_stat_input(params)
            result = self._calculate_hp(base_race, has_pers, final_iv)
            yield event.plain_result(f"基于 '{params}' 计算出的最终精力值为: {result}")
        except ValueError as ve:
            logger.warning(f"精力计算格式错误: {ve}")
            yield event.plain_result(f"输入错误: {ve}")
        except Exception as e:
            logger.error(f"精力计算出错: {e}")
            yield event.plain_result(f"计算出错，请检查输入格式。")

    @calculator.command("能力值计算")
    async def stat_calculator(self, event: AstrMessageEvent):
        """计算除精力外的其他五维能力值"""
        try:
            command_parts = event.message_str.split()
            if len(command_parts) < 3:
                yield event.plain_result("参数不能为空。用法: /计算器 能力值计算 186+性格+个体10")
                return
            params = " ".join(command_parts[2:])

            base_race, has_pers, final_iv = self._parse_stat_input(params)
            result = self._calculate_stat(base_race, has_pers, final_iv)
            yield event.plain_result(f"基于 '{params}' 计算出的最终能力值为: {result}")
        except ValueError as ve:
            logger.warning(f"能力值计算格式错误: {ve}")
            yield event.plain_result(f"输入错误: {ve}")
        except Exception as e:
            logger.error(f"能力值计算出错: {e}")
            yield event.plain_result(f"计算出错，请检查输入格式。")

    @calculator.command("伤害计算")
    async def damage_calculator(self, event: AstrMessageEvent, attack: int, defense: int, skill_power: int):
        try:
            result = self._calculate_damage(attack, defense, skill_power)
            yield event.plain_result(f"攻击 {attack}, 防御 {defense}, 威力 {skill_power} 的最终伤害为: {result}")
        except Exception as e:
            logger.error(f"伤害计算出错: {e}")
            yield event.plain_result(f"计算出错，请检查输入。")

    # --- 指令：反推系列 ---
    
    @filter.command("反推")
    async def reverse_main_help(self, event: AstrMessageEvent):
        """显示反推系列指令的总体帮助信息"""
        yield event.plain_result(self._get_main_reverse_help_text())

    @filter.command("精力反推")
    async def reverse_hp_analysis(self, event: AstrMessageEvent):
        """根据伤害和掉血百分比反推对方精力养成"""
        try:
            params_str = event.message_str.replace("精力反推", "", 1).strip()
            
            if not params_str or params_str.lower() == "帮助":
                yield event.plain_result(self._get_reverse_hp_help_text())
                return

            # 解析参数
            opponent_race, lost_hp_percent, actual_damage = None, None, None
            
            # 智能模式解析
            percent_match = re.search(r'掉血\s*(\d+\.?\d*)\s*%?', params_str)
            if percent_match:
                lost_hp_percent = float(percent_match.group(1))
                params_str = params_str.replace(percent_match.group(0), "", 1)
            
            damage_match = re.search(r'伤害\s*(\d+)', params_str)
            if damage_match:
                actual_damage = int(damage_match.group(1))
                params_str = params_str.replace(damage_match.group(0), "", 1)
            
            race_match = re.search(r'\d+', params_str)
            if race_match:
                opponent_race = int(race_match.group(0))

            # 快速模式解析 (如果智能模式没解析全)
            if None in [opponent_race, lost_hp_percent, actual_damage]:
                parts = re.findall(r'\d+\.?\d*', event.message_str.replace("精力反推", "", 1).strip())
                if len(parts) == 3:
                    opponent_race = int(parts[0])
                    lost_hp_percent = float(parts[1])
                    actual_damage = int(parts[2])
                else:
                    raise ValueError("参数不足或格式错误，需要3个数值：种族值、掉血百分比、伤害值。")
            
            if lost_hp_percent <= 0:
                raise ValueError("掉血百分比必须大于0。")

            # --- 核心计算与报告生成 ---
            estimated_total_hp = math.ceil(actual_damage / (lost_hp_percent / 100))
            
            scenarios = [
                {"name": "完全无养成", "pers": False, "iv": 0},
                {"name": "无性格+7点个体", "pers": False, "iv": 42},
                {"name": "无性格+8点个体", "pers": False, "iv": 48},
                {"name": "无性格+9点个体", "pers": False, "iv": 54},
                {"name": "无性格+满个体(10点)", "pers": False, "iv": 60},
                {"name": "仅性格", "pers": True, "iv": 0},
                {"name": "性格+7点个体", "pers": True, "iv": 42},
                {"name": "性格+8点个体", "pers": True, "iv": 48},
                {"name": "性格+9点个体", "pers": True, "iv": 54},
                {"name": "性格+满个体(10点)", "pers": True, "iv": 60},
            ]
            results = []
            for scenario in scenarios:
                hp = self._calculate_hp(opponent_race, scenario["pers"], scenario["iv"])
                results.append({"desc": scenario["name"], "hp": hp})
            
            sorted_by_hp = sorted(results, key=lambda x: x['hp'])
            
            analysis = "无法准确定位，请检查输入数值是否准确。"
            if estimated_total_hp < sorted_by_hp[0]['hp']:
                analysis = f"对方养成水平极低，估算精力({estimated_total_hp})低于最低模拟值({sorted_by_hp[0]['hp']})。"
            elif estimated_total_hp >= sorted_by_hp[-1]['hp']:
                analysis = f"对方养成水平极高，估算精力({estimated_total_hp})高于或等于满养成模拟值({sorted_by_hp[-1]['hp']})。"
            else:
                for i in range(len(sorted_by_hp) - 1):
                    if sorted_by_hp[i]['hp'] <= estimated_total_hp < sorted_by_hp[i+1]['hp']:
                        analysis = f"对方的精力养成情况最可能介于 [{sorted_by_hp[i]['desc']}] 和 [{sorted_by_hp[i+1]['desc']}] 之间。"
                        break
            
            report = (f"--- 精力反推分析 ---\n\n"
                      f"对方精力种族: {opponent_race}\n"
                      f"掉血百分比: {lost_hp_percent}%\n"
                      f"实际伤害: {actual_damage}\n\n"
                      f"==> 估算总精力: {estimated_total_hp}\n\n"
                      f"--- 精力模拟 (按从低到高) ---\n")
            
            for res in sorted_by_hp:
                report += f"> {res['desc']:<16} -> 模拟精力: {res['hp']}\n"
            
            report += f"\n--- 结论 ---\n您的估算总精力为 {estimated_total_hp}。\n{analysis}"
            yield event.plain_result(report)

        except ValueError as ve:
            logger.warning(f"精力反推参数解析出错: {ve}")
            yield event.plain_result(f"参数错误: {ve}\n\n输入 /精力反推 帮助 可查看详细帮助。")
        except Exception as e:
            logger.error(f"精力反推计算出错: {e}", exc_info=True)
            yield event.plain_result(f"计算出错，请检查您的输入格式是否正确。\n\n输入 /精力反推 帮助 可查看详细帮助。")


    @filter.command("反推防御")
    async def reverse_analysis(self, event: AstrMessageEvent):
        """
        根据战斗伤害反推对方的防御养成情况。支持智能模式和快速模式。
        """
        try:
            params_str_full = event.message_str.replace("反推防御", "", 1).strip()
            
            if not params_str_full or params_str_full.lower() == "帮助":
                yield event.plain_result(self._get_reverse_help_text())
                return

            parts = params_str_full.split()
            intelligent_mode_markers = ['+', '我方', '对方', '威力', '伤害', '性格', '个体']
            contains_markers = any(marker in params_str_full for marker in intelligent_mode_markers)
            is_quick_mode = len(parts) == 4 and not contains_markers

            player_input_str, opponent_race_str, skill_power, actual_damage = "", "", 0, 0
            my_base_race, my_has_pers, my_final_iv, opponent_race = 0, False, 0, 0
            
            if is_quick_mode:
                player_input_str, opponent_race_str, skill_power, actual_damage = parts[0], parts[1], int(parts[2]), int(parts[3])
                my_base_race, my_has_pers, my_final_iv = self._parse_quick_mode_attacker(player_input_str)
                opponent_race = int(opponent_race_str)
            else: # 智能模式
                fixed_pattern = r"(威力|伤害)\s*(\d+)|(\d+)\s*(威力|伤害)"
                fixed_matches = re.findall(fixed_pattern, params_str_full)
                
                params = {}
                remaining_str = params_str_full
                for key1, val1, val2, key2 in fixed_matches:
                    key = key1 or key2
                    val = int(val1 or val2)
                    params[key] = val
                    remaining_str = re.sub(fr"{key}\s*{val}|{val}\s*{key}", "", remaining_str, 1)

                if "威力" not in params or "伤害" not in params:
                    yield event.plain_result("缺少【威力】或【伤害】参数。\n\n输入 /反推防御 帮助 可查看详细帮助。")
                    return
                skill_power, actual_damage = params["威力"], params["伤害"]

                stat_pattern = r"((?:我方|对方)?\s*\d+(?:\s*\+\s*性格|\s*\+\s*个体(?:\d+)?)?)"
                stat_blocks = [s.strip() for s in re.findall(stat_pattern, remaining_str) if s.strip()]
                
                if len(stat_blocks) != 2:
                    yield event.plain_result("输入错误：未能识别出我方和对方的种族值信息。请确保提供了两个数值（例如 '我方186+性格' 和 '对方80'，或 '186 80'）。\n\n输入 /反推防御 帮助 可查看详细帮助。")
                    return
                
                b1, b2 = stat_blocks[0], stat_blocks[1]
                
                def get_block_type(block_str):
                    if any(kw in block_str for kw in ['我方', '性格', '个体']): return 'player'
                    if '对方' in block_str: return 'opponent'
                    return 'neutral'

                type1, type2 = get_block_type(b1), get_block_type(b2)

                if type1 == 'player' and type2 == 'opponent': player_input_str, opponent_race_str = b1, b2
                elif type1 == 'opponent' and type2 == 'player': player_input_str, opponent_race_str = b2, b1
                elif type1 == 'player' and type2 == 'neutral': player_input_str, opponent_race_str = b1, b2
                elif type1 == 'neutral' and type2 == 'player': player_input_str, opponent_race_str = b2, b1
                elif type1 == 'opponent' and type2 == 'neutral': player_input_str, opponent_race_str = b2, b1
                elif type1 == 'neutral' and type2 == 'opponent': player_input_str, opponent_race_str = b1, b2
                elif type1 == 'neutral' and type2 == 'neutral':
                    if params_str_full.find(b1) < params_str_full.find(b2): player_input_str, opponent_race_str = b1, b2
                    else: player_input_str, opponent_race_str = b2, b1
                else:
                    yield event.plain_result("输入冲突：无法明确区分我方和对方。请检查您的输入，例如 '我方186+性格' 和 '对方80'。")
                    return
                
                opponent_race = int(re.search(r"\d+", opponent_race_str).group(0))
                my_base_race, my_has_pers, my_final_iv = self._parse_stat_input(player_input_str)

            my_attack = self._calculate_stat(my_base_race, my_has_pers, my_final_iv)
            
            scenarios = [
                {"name": "完全无养成", "pers": False, "iv": 0},
                {"name": "无性格+7点个体", "pers": False, "iv": 42},
                {"name": "无性格+8点个体", "pers": False, "iv": 48},
                {"name": "无性格+9点个体", "pers": False, "iv": 54},
                {"name": "无性格+满个体(10点)", "pers": False, "iv": 60},
                {"name": "仅性格", "pers": True, "iv": 0},
                {"name": "性格+7点个体", "pers": True, "iv": 42},
                {"name": "性格+8点个体", "pers": True, "iv": 48},
                {"name": "性格+9点个体", "pers": True, "iv": 54},
                {"name": "性格+满个体(10点)", "pers": True, "iv": 60},
            ]
            results = []
            for scenario in scenarios:
                defense = self._calculate_stat(opponent_race, scenario["pers"], scenario["iv"])
                damage = self._calculate_damage(my_attack, defense, skill_power)
                results.append({"desc": scenario["name"], "def": defense, "dmg": damage})
            
            sorted_by_dmg = sorted(results, key=lambda x: x['dmg'], reverse=True)
            
            analysis = "无法准确定位，请检查伤害值是否准确。"
            if actual_damage > sorted_by_dmg[0]['dmg']: analysis = "对方可能完全没有养成，或养成水平极低。"
            elif actual_damage <= sorted_by_dmg[-1]['dmg']: analysis = "对方养成水平极高，伤害已低于或等于满养成模拟值。"
            else:
                for i in range(len(sorted_by_dmg) - 1):
                    if sorted_by_dmg[i]['dmg'] >= actual_damage > sorted_by_dmg[i+1]['dmg']:
                        analysis = f"对方的养成情况最可能介于 [{sorted_by_dmg[i]['desc']}] 和 [{sorted_by_dmg[i+1]['desc']}] 之间。"
                        break
            
            report = (f"--- 伤害反推(防御)分析 ---\n\n"
                      f"我方攻击: {my_attack} (基于 {player_input_str.strip()})\n"
                      f"对方防御种族: {opponent_race}\n"
                      f"技能威力: {skill_power}\n"
                      f"实际造成伤害: {actual_damage}\n\n"
                      f"--- 伤害模拟 (按对方防御从低到高) ---\n")
            
            for res in sorted(results, key=lambda x: x['def']):
                report += f"> {res['desc']:<16} (防御: {res['def']}) -> 预计伤害: {res['dmg']}\n"
            
            report += f"\n--- 结论 ---\n您造成的实际伤害为 {actual_damage}。\n{analysis}"
            yield event.plain_result(report)

        except ValueError as ve:
            logger.warning(f"反推防御参数解析出错: {ve}")
            yield event.plain_result(f"参数错误: {ve}\n\n输入 /反推防御 帮助 可查看详细帮助。")
        except Exception as e:
            logger.error(f"反推防御计算出错: {e}", exc_info=True)
            yield event.plain_result(f"计算出错，请检查您的输入格式是否正确。\n\n输入 /反推防御 帮助 可查看详细帮助。")

    @filter.command("反推攻击")
    async def reverse_attack_analysis(self, event: AstrMessageEvent):
        """
        根据受到的战斗伤害反推对方的攻击养成情况。支持智能模式和快速模式。
        """
        try:
            params_str_full = event.message_str.replace("反推攻击", "", 1).strip()
            
            if not params_str_full or params_str_full.lower() == "帮助":
                yield event.plain_result(self._get_reverse_attack_help_text())
                return

            parts = params_str_full.split()
            intelligent_mode_markers = ['+', '我方', '对方', '威力', '伤害', '性格', '个体']
            contains_markers = any(marker in params_str_full for marker in intelligent_mode_markers)
            is_quick_mode = len(parts) == 4 and not contains_markers

            player_input_str, opponent_race_str, skill_power, actual_damage = "", "", 0, 0
            my_base_race, my_has_pers, my_final_iv, opponent_race = 0, False, 0, 0
            
            if is_quick_mode:
                player_input_str, opponent_race_str, skill_power, actual_damage = parts[0], parts[1], int(parts[2]), int(parts[3])
                my_base_race, my_has_pers, my_final_iv = self._parse_quick_mode_attacker(player_input_str)
                opponent_race = int(opponent_race_str)
            else: # 智能模式
                fixed_pattern = r"(威力|伤害)\s*(\d+)|(\d+)\s*(威力|伤害)"
                fixed_matches = re.findall(fixed_pattern, params_str_full)
                
                params = {}
                remaining_str = params_str_full
                for key1, val1, val2, key2 in fixed_matches:
                    key = key1 or key2
                    val = int(val1 or val2)
                    params[key] = val
                    remaining_str = re.sub(fr"{key}\s*{val}|{val}\s*{key}", "", remaining_str, 1)

                if "威力" not in params or "伤害" not in params:
                    yield event.plain_result("缺少【威力】或【伤害】参数。\n\n输入 /反推攻击 帮助 可查看详细帮助。")
                    return
                
                skill_power, actual_damage = params["威力"], params["伤害"]

                stat_pattern = r"((?:我方|对方)?\s*\d+(?:\s*\+\s*性格|\s*\+\s*个体(?:\d+)?)?)"
                stat_blocks = [s.strip() for s in re.findall(stat_pattern, remaining_str) if s.strip()]
                
                if len(stat_blocks) != 2:
                    yield event.plain_result("输入错误：未能识别出我方和对方的种族值信息。请确保提供了两个数值（例如 '我方100+性格' 和 '对方186'，或 '100 186'）。\n\n输入 /反推攻击 帮助 可查看详细帮助。")
                    return

                b1, b2 = stat_blocks[0], stat_blocks[1]

                def get_block_type(block_str):
                    if any(kw in block_str for kw in ['我方', '性格', '个体']): return 'player'
                    if '对方' in block_str: return 'opponent'
                    return 'neutral'

                type1, type2 = get_block_type(b1), get_block_type(b2)

                if type1 == 'player' and type2 == 'opponent': player_input_str, opponent_race_str = b1, b2
                elif type1 == 'opponent' and type2 == 'player': player_input_str, opponent_race_str = b2, b1
                elif type1 == 'player' and type2 == 'neutral': player_input_str, opponent_race_str = b1, b2
                elif type1 == 'neutral' and type2 == 'player': player_input_str, opponent_race_str = b2, b1
                elif type1 == 'opponent' and type2 == 'neutral': player_input_str, opponent_race_str = b2, b1
                elif type1 == 'neutral' and type2 == 'opponent': player_input_str, opponent_race_str = b1, b2
                elif type1 == 'neutral' and type2 == 'neutral':
                    if params_str_full.find(b1) < params_str_full.find(b2): player_input_str, opponent_race_str = b1, b2
                    else: player_input_str, opponent_race_str = b2, b1
                else:
                    yield event.plain_result("输入冲突：无法明确区分我方和对方。请检查您的输入，例如 '我方100+性格' 和 '对方186'。")
                    return
                
                opponent_race = int(re.search(r"\d+", opponent_race_str).group(0))
                my_base_race, my_has_pers, my_final_iv = self._parse_stat_input(player_input_str)

            my_defense = self._calculate_stat(my_base_race, my_has_pers, my_final_iv)
            
            scenarios = [
                {"name": "完全无养成", "pers": False, "iv": 0},
                {"name": "无性格+7点个体", "pers": False, "iv": 42},
                {"name": "无性格+8点个体", "pers": False, "iv": 48},
                {"name": "无性格+9点个体", "pers": False, "iv": 54},
                {"name": "无性格+满个体(10点)", "pers": False, "iv": 60},
                {"name": "仅性格", "pers": True, "iv": 0},
                {"name": "性格+7点个体", "pers": True, "iv": 42},
                {"name": "性格+8点个体", "pers": True, "iv": 48},
                {"name": "性格+9点个体", "pers": True, "iv": 54},
                {"name": "性格+满个体(10点)", "pers": True, "iv": 60},
            ]
            results = []
            for scenario in scenarios:
                opponent_attack = self._calculate_stat(opponent_race, scenario["pers"], scenario["iv"])
                damage = self._calculate_damage(opponent_attack, my_defense, skill_power)
                results.append({"desc": scenario["name"], "atk": opponent_attack, "dmg": damage})
            
            sorted_by_dmg = sorted(results, key=lambda x: x['dmg'])
            
            analysis = "无法准确定位，请检查伤害值是否准确。"
            if actual_damage < sorted_by_dmg[0]['dmg']: analysis = "对方可能完全没有养成，或养成水平极低。"
            elif actual_damage >= sorted_by_dmg[-1]['dmg']: analysis = "对方养成水平极高，伤害已高于或等于满养成模拟值。"
            else:
                for i in range(len(sorted_by_dmg) - 1):
                    if sorted_by_dmg[i]['dmg'] <= actual_damage < sorted_by_dmg[i+1]['dmg']:
                        analysis = f"对方的养成情况最可能介于 [{sorted_by_dmg[i]['desc']}] 和 [{sorted_by_dmg[i+1]['desc']}] 之间。"
                        break
            
            report = (f"--- 伤害反推(攻击)分析 ---\n\n"
                      f"我方防御: {my_defense} (基于 {player_input_str.strip()})\n"
                      f"对方攻击种族: {opponent_race}\n"
                      f"技能威力: {skill_power}\n"
                      f"实际受到伤害: {actual_damage}\n\n"
                      f"--- 伤害模拟 (按对方攻击从低到高) ---\n")
            
            for res in sorted(results, key=lambda x: x['atk']):
                report += f"> {res['desc']:<16} (攻击: {res['atk']}) -> 预计伤害: {res['dmg']}\n"
            
            report += f"\n--- 结论 ---\n您受到的实际伤害为 {actual_damage}。\n{analysis}"
            yield event.plain_result(report)

        except ValueError as ve:
            logger.warning(f"反推攻击参数解析出错: {ve}")
            yield event.plain_result(f"参数错误: {ve}\n\n输入 /反推攻击 帮助 可查看详细帮助。")
        except Exception as e:
            logger.error(f"反推攻击计算出错: {e}", exc_info=True)
            yield event.plain_result(f"计算出错，请检查您的输入格式是否正确。\n\n输入 /反推攻击 帮助 可查看详细帮助。")