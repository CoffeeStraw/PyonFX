"""
Community example - 'Dangos' karaoke effect.

This script animates a troupe of "dango" blobs that morph out of every
romanji syllable and leave the stage with a playful exit.

Forged by CoffeeStraw, yet destined to be shaped by the entire community:
together we will build the world's first open-source, collaborative KFX!
Leave your mark, now. (ง •̀_•́)ง

File structure:
1) Dango class: represents one dango. It has a state, representing its geometry/style (`self.shape_parts`, `self.style_config`),
   properties (`self.x`, `self.y`, `self.frz`, `self.fscx`, `self.fscy`, `self.alpha`),
   and a timeline cursor (`self.current_time`). It provides an animation API
   (e.g. `idle`, `move_to`, `morph_from_shapes` and all the exit animations),
   each updating state and the time cursor.
2) Per-line processing: `process_romaji_line` instantiates one Dango
   per visible character, drives its morphing from the glyph and picks
   an `exit_*` routine;
3) Basic leadin/main effect in `leadin_effect` and `main_effect` functions.

Adding a new exit animation:
1) Implement `def exit_your_idea(self, **timing) -> "Dango":` inside
   Dango. Iterate with `FrameUtility`, update `self.x/y/...`, call
   `self._render_frame` every frame, advance `self.current_time` and
   `return self`;
2) Register your method in the `exit_effects` map inside
   `process_romaji_line` so it can be picked for the appropriate
   variant.

Follow PEP-8, keep the method side-effect-free apart from tweaking
`self.*` fields, and have fun animating!
"""

import math
import random
from copy import deepcopy
from typing import Literal

from dango_config import (
    DANGO_ALTERNATIVES,
    RENDER_ORDER,
    VARIANT_BASE_CONFIGS,
    VARIANT_LOOKUP,
)

from pyonfx import *

# Load ASS file
io = Ass("in.ass")
meta, styles, lines = io.get_data()


class Dango:
    def __init__(
        self,
        name: str,
        x: float,
        y: float,
        current_time: int,
        shape_parts: dict[str, Shape],
        style_config: dict[str, dict[str, str | float]],
        line_template: Line,
    ):
        self.name = name
        self.x = x
        self.y = y
        self.frz = 0
        self.fscx = 100
        self.fscy = 100
        self.alpha = 0
        self.line_template = line_template

        # Dynamic shape parts and styles
        self.shape_parts: dict[str, Shape] = {}
        self.style_config: dict[str, dict[str, str | float]] = {}

        # Animation state
        self.current_time = current_time
        self.base_layer = 0

        # Load variant data
        self.load_variant(shape_parts, style_config)

    def load_variant(
        self,
        shape_parts: dict[str, Shape],
        style_config: dict[str, dict[str, str | float]],
    ) -> "Dango":
        """Load shapes and styles from a variant definition."""
        # Deep copy shapes and styles
        self.shape_parts = deepcopy(shape_parts)
        self.style_config = deepcopy(style_config)

        # Randomly shift eyes position
        if "eyes" in self.shape_parts and self.name == "base":
            self.shape_parts["eyes"].move(random.uniform(-4, 4), 0)
        return self

    def _create_style_tags_for_properties(self) -> str:
        """Create ASS style tags for internal properties."""
        tags = [f"\\pos({self.x:.3f},{self.y:.3f})"]

        if self.frz != 0:
            tags.append(f"\\frz{self.frz:.3f}")
        if self.fscx != 100:
            tags.append(f"\\fscx{self.fscx:.3f}")
        if self.fscy != 100:
            tags.append(f"\\fscy{self.fscy:.3f}")

        return "".join(tags)

    def _create_style_tags(self, part_name: str) -> str:
        """Create ASS style tags for a part, handling None values with defaults."""
        part_style = self.style_config[part_name]
        tags = [f"\\alpha{Convert.alpha_dec_to_ass(self.alpha)}"]

        # Handle part_style config
        for color_key in ["1c", "3c"]:
            if color_key in part_style and part_style[color_key] is not None:
                tags.append(f"\\{color_key}{part_style[color_key]}")
        bord = part_style.get("bord", 0)
        if bord is not None:
            tags.append(f"\\bord{bord:.3f}")

        # Handle internal properties
        tags.extend(self._create_style_tags_for_properties())

        return "".join(tags)

    def _create_interpolated_style_tags(
        self,
        progress: float,
        source_style: dict[str, str | float],
        target_style: dict[str, str | float],
    ) -> str:
        """Create ASS style tags for interpolated styling during morph."""
        tags = []

        # Handle primary/outline color
        for color_key in ["1c", "3c"]:
            if color_key not in target_style:
                continue
            if not source_style:
                tags.append(f"\\{color_key}{target_style[color_key]}")
                continue

            start_color = source_style[color_key]
            end_color = target_style[color_key]
            assert isinstance(start_color, str) and isinstance(end_color, str)

            interpolated_color = Utils.interpolate(progress, start_color, end_color)
            tags.append(f"\\{color_key}{interpolated_color}")

        # Handle 1a and 3a
        for alpha_key in ["1a", "3a"]:
            # Interpolate in-between source 1a/3a and 0.0
            start_alpha = 0.0 if not source_style else source_style[alpha_key]
            end_alpha = 0.0
            assert isinstance(start_alpha, float) and isinstance(end_alpha, float)
            interpolated_alpha = Utils.interpolate(progress, start_alpha, end_alpha)
            tags.append(f"\\{alpha_key}{Convert.alpha_dec_to_ass(interpolated_alpha)}")

        # Handle border thickness
        start_border = 0.0 if not source_style else source_style.get("bord", 0.0)
        end_border = target_style.get("bord", 0.0)
        assert isinstance(start_border, float) and isinstance(end_border, float)
        border_value = Utils.interpolate(progress, start_border, end_border)
        tags.append(f"\\bord{border_value:.3f}")

        # Add properties tags
        tags.append(self._create_style_tags_for_properties())

        return "".join(tags)

    def _render_frame(
        self, start_time: int, end_time: int, layer_offset: int = 0
    ) -> None:
        """Render current dango state to a single frame."""

        for part_name, shape in self.shape_parts.items():
            l = self.line_template.copy()
            l.layer = self.base_layer + layer_offset
            l.start_time = start_time
            l.end_time = end_time

            style_tags = self._create_style_tags(part_name)

            l.text = f"{{\\an7{style_tags}\\p1}}{shape}"
            io.write_line(l)

    @io.track
    def morph_from_shapes(
        self,
        source_shape_parts: dict[str, Shape],
        source_style_config: dict[str, dict[str, str | float]],
        duration: int,
        layer_offset: int = 0,
    ) -> "Dango":
        """Morph from source shapes to this dango over duration."""
        frame_util = FrameUtility(
            self.current_time, self.current_time + duration, meta.timestamps
        )
        for start, end, frame_idx, total_frames in frame_util:
            progress = frame_idx / total_frames

            # Morph source shape to dango shape
            morphed_chunks = Shape.morph_multi(
                source_shape_parts, self.shape_parts, progress, ensure_shell_pairs=False
            )
            # Sort morphed items based on target ID render order
            morphed_items = sorted(
                morphed_chunks.items(),
                key=lambda item: (
                    RENDER_ORDER.index(item[0][1])
                    if item[0][1] in RENDER_ORDER
                    else float("-inf")
                ),
            )

            # Render each morphed shape
            for (src_id, tgt_id), morphed_shape in morphed_items:
                l = self.line_template.copy()
                l.layer = self.base_layer + layer_offset
                l.start_time = start
                l.end_time = end

                # Create interpolated style tags
                style_tags = self._create_interpolated_style_tags(
                    progress,
                    source_style_config.get(src_id or "", {}),
                    self.style_config.get(tgt_id or "", {}),
                )

                l.text = f"{{\\an7\\pos({self.x:.3f},{self.y:.3f}){style_tags}\\p1}}{morphed_shape}"
                io.write_line(l)

        self.current_time += duration
        return self

    def idle(
        self,
        animation_type: Literal["static", "bounce", "angry_shake"],
        duration: int,
        settle_ms: int = 150,
        layer_offset: int = 0,
    ) -> "Dango":
        """Play idle animation for *duration* ms.

        The last ``settle_ms`` milliseconds will smoothly damp the motion so the
        dango returns to its neutral pose instead of stopping abruptly.
        """
        # Handle animated cases frame by frame
        settle_start = max(0, duration - settle_ms)
        frame_util = FrameUtility(
            self.current_time, self.current_time + duration, meta.timestamps
        )

        # Handle static case with single render
        if animation_type == "static":
            frame_util_frames = list(frame_util)
            start_time = frame_util_frames[0][0]
            end_time = frame_util_frames[-1][1]
            self._render_frame(start_time, end_time, layer_offset)
            self.current_time += end_time - start_time
            return self

        start_x, start_y = self.x, self.y

        for start, end, _, _ in frame_util:
            elapsed = start - self.current_time

            # 0→1 factor that linearly goes to 0 after settle_start
            damp = 1.0
            if elapsed >= settle_start:
                damp = 1 - (elapsed - settle_start) / settle_ms

            # Different idle animation types
            if animation_type == "bounce":
                bounce_amplitude = 4
                bounce_period = 400
                offset_y = (
                    bounce_amplitude
                    * damp
                    * math.sin(2 * math.pi * elapsed / bounce_period)
                )
                self.y = start_y + offset_y
                self._render_frame(start, end, layer_offset)

            elif animation_type == "angry_shake":
                shake_amplitude = 3
                shake_period = 150
                cur_amp = shake_amplitude * damp
                dx = random.uniform(-cur_amp, cur_amp)
                self.x = start_x + dx
                self.frz = shake_amplitude * math.sin(
                    2 * math.pi * elapsed / shake_period
                )
                self._render_frame(start, end, layer_offset)

        self.current_time += duration
        return self

    def move_to(
        self,
        new_x: float,
        new_y: float,
        duration: int,
        easing: Literal["in_back", "out_cubic"] | float = 1.0,
        layer_offset: int = 0,
        fade_duration: int | None = None,
    ) -> "Dango":
        """Animate movement to new position with optional fade-out."""
        frame_util = FrameUtility(
            self.current_time, self.current_time + duration, meta.timestamps
        )

        start_x, start_y = self.x, self.y
        start_alpha = self.alpha

        for start, end, frame_idx, total_frames in frame_util:
            progress = frame_idx / total_frames

            # Update position
            self.x = Utils.interpolate(progress, start_x, new_x, easing)
            self.y = Utils.interpolate(progress, start_y, new_y, easing)

            # Apply fade-out if requested
            if fade_duration is not None:
                elapsed = start - self.current_time
                fade_start = max(0, duration - fade_duration)
                if elapsed >= fade_start:
                    self.alpha = start_alpha
                    self.alpha += frame_util.add(
                        fade_start, duration, 255 - start_alpha
                    )
                else:
                    self.alpha = start_alpha

            self._render_frame(start, end, layer_offset)

        self.current_time += duration
        return self

    @io.track
    def exit_jump_down_fall(
        self,
        charge_duration: int = 100,
        jump_duration: int = 300,
        fall_duration: int = 650,
        fade_duration: int = 300,
        jump_height: int = 30,
        fall_distance: int = 60,
        charge_offset: float = 6.0,
        charge_fscy: float = 85,
        up_fscx: float = 70,
        up_fscy: float = 125,
        max_x_offset: int = 10,
    ) -> "Dango":
        """Exit jump sequence with squash-and-stretch charging animation."""
        start_x, start_y = self.x, self.y
        drift_x_final = random.uniform(-max_x_offset, max_x_offset)

        total_duration = charge_duration + jump_duration + fall_duration
        frame_util = FrameUtility(
            self.current_time, self.current_time + total_duration, meta.timestamps
        )

        for f_start, f_end, _, _ in frame_util:
            # Reset properties to defaults for each frame
            self.x, self.y = start_x, start_y
            self.fscx, self.fscy = 100, 100
            self.frz, self.alpha = 0, 0

            # 1. Crouch (downwards)
            self.y += frame_util.add(0, charge_duration, charge_offset)
            self.fscy += frame_util.add(0, charge_duration, charge_fscy - 100)

            # 2. Jump up (to peak)
            self.x += frame_util.add(charge_duration, total_duration, drift_x_final)
            self.y += frame_util.add(
                charge_duration, jump_duration, -jump_height - charge_offset, 0.8
            )
            self.fscx += frame_util.add(
                charge_duration,
                jump_duration,
                up_fscx - 100,
            )
            self.fscy += frame_util.add(
                charge_duration,
                jump_duration,
                up_fscy - charge_fscy,
            )

            # 3. Fall down past start
            self.y += frame_util.add(
                jump_duration,
                total_duration,
                jump_height + fall_distance,
                1.3,
            )
            self.fscy += frame_util.add(
                jump_duration,
                total_duration,
                100 - up_fscy,
                0.5,
            )
            self.fscx += frame_util.add(
                jump_duration,
                total_duration,
                100 - up_fscx,
                0.5,
            )

            # Fade-out
            self.alpha += frame_util.add(
                total_duration - fade_duration, total_duration, 255
            )

            # Render frame
            self._render_frame(f_start, f_end)

        # Reset scale for future animations
        self.fscx, self.fscy = 100, 100
        self.current_time += total_duration
        return self

    @io.track
    def exit_furious_dash(
        self,
        shake_duration: int = 2000,
        dash_duration: int = 800,
        fade_duration: int = 300,
        dash_distance: int = -200,
    ) -> "Dango":
        """Angry-specific exit: brief shake in place, then a fast left dash off-screen with fade-out."""
        # Phase 1: Shake in place using existing idle animation
        self.idle("angry_shake", shake_duration)

        # Phase 2: Dash movement with fade-out using enhanced move_to
        target_x = self.x + dash_distance
        self.move_to(
            target_x, self.y, dash_duration, "in_back", fade_duration=fade_duration
        )

        return self

    @io.track
    def exit_slow_steps(
        self,
        duration: int = 3000,
        steps: int = 3,
        fade_duration: int = 2000,
        drift_distance: int = 50,
    ) -> "Dango":
        """Old-specific: slow stepped movement using multiple move_to calls."""
        # Grandpa moves left, others move right
        dx_final = -drift_distance if self.name == "grandpa" else drift_distance

        # Calculate step parameters
        step_duration = duration // steps
        remaining_duration = duration - (
            step_duration * (steps - 1)
        )  # Last step gets any remainder
        dx_per_step = dx_final / steps

        # Execute stepped movement
        for step in range(steps):
            target_x = self.x + dx_per_step
            current_step_duration = (
                remaining_duration if step == steps - 1 else step_duration
            )

            # Only apply fade-out on the last step
            fade_for_step = fade_duration if step == steps - 1 else None

            self.move_to(
                target_x,
                self.y,
                current_step_duration,
                "out_cubic",
                fade_duration=fade_for_step,
            )

        return self

    @io.track
    def exit_heart_spiral(
        self,
        hold_duration: int = 1300,
        move_duration: int = 1500,
        fade_duration: int = 400,
        loops: int = 2,
        spiral_amplitude: int = 10,
        vertical_travel: int = -80,
        drift_x_total: int = -20,
    ) -> "Dango":
        """Cute-specific exit: ascend in corkscrew path leaving fading hearts."""

        # Phase 1: Gradual drift left
        drift_target_x = self.x + drift_x_total
        self.move_to(drift_target_x, self.y, hold_duration, "out_cubic")

        # Phase 2: Spiral motion phase (custom animation for complex movement)
        start_x, start_y = self.x, self.y
        frame_util = FrameUtility(
            self.current_time, self.current_time + move_duration, meta.timestamps
        )

        for f_start, f_end, frame_idx, _ in frame_util:
            elapsed = max(0, f_start - self.current_time)
            move_p = elapsed / move_duration

            # Reset position and properties each frame
            self.x, self.y = start_x, start_y
            self.frz = 0
            self.alpha = 0

            # Spiral motion
            angle = move_p * loops * 2 * math.pi
            spiral_x = spiral_amplitude * math.sin(angle) * (1 - move_p)

            self.x += spiral_x
            self.y += Utils.interpolate(move_p, 0, vertical_travel)
            self.frz = 15 * math.sin(angle)

            # Fade during final portion
            if elapsed >= move_duration - fade_duration:
                fade_p = (elapsed - (move_duration - fade_duration)) / fade_duration
                self.alpha = Utils.interpolate(fade_p, 0, 255)

            # Render
            self._render_frame(f_start, f_end)

            # Spawn hearts during spiral motion
            if frame_idx % 5 == 0:
                self._spawn_heart(f_start)

        self.current_time += move_duration
        return self

    @io.track
    def piggyback_onto(
        self,
        carrier: "Dango",
        *,
        climb_duration: int = 500,
        travel_duration: int = 1000,
        fade_duration: int = 400,
        fall_duration: int = 600,
        dx_travel: int = -80,
        fall_distance: int = 80,
        heavy_prob: float = 0.4,
        balancing_prob: float = 0.6,
        slip_prob: float = 0.35,
        xd_prob: float = 0.25,
    ) -> "Dango":
        """Ride *carrier* dango with optional wobble, balance and slip variations.

        Total duration is climb_duration + travel_duration, of which fade_duration is the last part spent fading out and fall_duration is the last part spent falling.
        """
        # Alternate eye shapes
        XD_EYES: Shape = DANGO_ALTERNATIVES["eyes"][0]
        SPIRAL_EYES: Shape = DANGO_ALTERNATIVES["eyes"][1]

        # Initial state / randomised variations
        is_heavy = random.random() < heavy_prob
        is_balancing = True if is_heavy else (random.random() < balancing_prob)
        is_slip = False if is_heavy else (random.random() < slip_prob)
        use_xd_upper = random.random() < xd_prob

        # Replace xD eyes permanently
        if use_xd_upper:
            self.shape_parts["eyes"] = XD_EYES

        # Idle to align both dangos
        if self.current_time < carrier.current_time:
            self.idle(
                "bounce", carrier.current_time - self.current_time, layer_offset=1
            )
        elif carrier.current_time < self.current_time:
            carrier.idle("bounce", self.current_time - carrier.current_time)

        # Climb phase
        carrier_x = carrier.x
        carrier_y = carrier.y
        self_x = carrier_x
        self_y = carrier_y - 18
        self.move_to(self_x, self_y, climb_duration, "out_cubic", layer_offset=1)
        carrier.idle("static", climb_duration)

        # Travel phase
        if is_heavy:
            carrier.shape_parts["eyes"] = SPIRAL_EYES

        start_time = self.current_time
        frame_util = FrameUtility(
            start_time, start_time + travel_duration, meta.timestamps
        )
        slip_trigger = travel_duration - fall_duration

        # Travel phase
        for f_start, f_end, _, _ in frame_util:
            elapsed = max(0, f_start - start_time)

            # Reset dynamic props for both dangos each frame
            self.x, self.y = self_x, self_y
            self.fscx, self.fscy = 100, 100
            self.frz, self.alpha = 0, 0
            carrier.x, carrier.y = carrier_x, carrier_y
            carrier.fscx, carrier.fscy = 100, 100
            carrier.frz, carrier.alpha = 0, 0

            # Travel (both)
            self.x += frame_util.add(0, travel_duration, dx_travel)
            carrier.x += frame_util.add(0, travel_duration, dx_travel)

            # Heavy wobble (lower)
            if is_heavy:
                wobble_period = 500
                wobble_ampl = 12
                wobble_phase = elapsed / wobble_period * 2 * math.pi
                carrier.fscy = 100 - wobble_ampl * abs(math.sin(wobble_phase))

            # Balancing (upper)
            if is_balancing and not (is_slip and elapsed >= fall_duration):
                bal_period = 600
                bal_ampl_rot = 8
                bal_phase = elapsed / bal_period * 2 * math.pi
                rot = bal_ampl_rot * math.sin(bal_phase)
                self.frz = rot
                self.fscy = 100 - 8 * abs(math.sin(bal_phase))

            # Slip / Fall (upper)
            if is_slip and elapsed >= slip_trigger:
                # change eyes to spiral while falling
                self.shape_parts["eyes"] = SPIRAL_EYES

                t_fall = elapsed - slip_trigger
                p = t_fall / fall_duration  # 0→1
                fall_offset = (p**2) * fall_distance  # ease-in
                horiz_factor = 1 - 0.7 * p  # 1 → 0.3

                self.y += fall_offset
                self.x = carrier.x * horiz_factor + (1 - horiz_factor) * self_x

            # Fades (both)
            carrier.alpha += frame_util.add(
                travel_duration - fade_duration, travel_duration, 255
            )
            self.alpha += frame_util.add(
                travel_duration - fade_duration, travel_duration, 255
            )

            # Render
            carrier._render_frame(f_start, f_end, 0)
            self._render_frame(f_start, f_end, 1)

        self.current_time = carrier.current_time = start_time + travel_duration
        return self

    @io.track
    def tug_away(
        self,
        target: "Dango",
        pre_duration: int = 400,
        drag_duration: int = 1800,
        fade_duration: int = 500,
        gap: int = 20,
        drag_distance: int = 300,
    ) -> "Dango":
        """Angry grabs cute and drags her away, leaving hearts."""
        # Sync timing - both start at the same time
        if self.current_time < target.current_time:
            self.idle("angry_shake", target.current_time - self.current_time)
        elif target.current_time < self.current_time:
            target.idle("static", self.current_time - target.current_time)

        # Phase 1: Angry approaches cute
        approach_target_x = target.x + gap
        self.move_to(
            approach_target_x, self.y, pre_duration, "out_cubic", layer_offset=1
        )
        target.idle("static", pre_duration, layer_offset=0)

        # Phase 2: Both move together in drag motion with fade-out
        start_x_angry, start_x_cute = self.x, target.x
        frame_util = FrameUtility(
            self.current_time, self.current_time + drag_duration, meta.timestamps
        )

        for f_start, f_end, _, _ in frame_util:
            # Reset dynamic properties for the current frame
            self.x, target.x = start_x_angry, start_x_cute
            self.frz = self.alpha = 0
            target.frz = target.alpha = 0

            # Horizontal drag motion
            move_offset = frame_util.add(0, drag_duration, drag_distance, 0.8)
            self.x += move_offset
            target.x += move_offset

            # Fade-out during the last part of the drag
            fade_alpha = frame_util.add(
                drag_duration - fade_duration, drag_duration, 255
            )
            self.alpha = fade_alpha
            target.alpha = fade_alpha

            # Render both dangos (angry above cute)
            self._render_frame(f_start, f_end, layer_offset=1)
            target._render_frame(f_start, f_end, layer_offset=0)

            # Spawn hearts during drag phase (25% chance per frame)
            if random.random() < 0.25:
                target._spawn_heart(f_start)

        # Update final state
        self.current_time = target.current_time = self.current_time + drag_duration
        return self

    def _spawn_heart(self, start_time: int) -> None:
        """Spawn a heart particle from dango's current position."""
        trail_dur = random.randint(450, 650)
        dx_rand = random.uniform(-15, 15)
        dy_fall = random.uniform(25, 50)
        scale_start = random.uniform(50, 80)
        scale_end = scale_start + random.uniform(40, 60)
        rot_h = random.uniform(-30, 30)

        h = self.line_template.copy()
        h.layer = max(0, self.base_layer - 1)
        h.start_time = start_time
        h.end_time = start_time + trail_dur

        heart_tags = (
            f"\\1c&HB0A8F5&\\3c&H7370DF&\\bord1"
            f"\\fscx{scale_start:.0f}\\fscy{scale_start:.0f}"
            f"\\move({self.x:.3f},{self.y:.3f},{self.x + dx_rand:.3f},{self.y + dy_fall:.3f})"
            f"\\t(0,{trail_dur // 2},\\fscx{scale_end:.0f}\\fscy{scale_end:.0f})"
            f"\\frz{rot_h:.1f}"
            f"\\fad(0,{trail_dur})"
        )

        h.text = f"{{\\an7{heart_tags}\\p1}}{Shape.heart(8)}"
        io.write_line(h)


@io.track
def leadin_effect(
    line: Line,
    char: Char,
    dango_style: dict[str, dict[str, str | float]],
):
    l = line.copy()
    l.layer = 5

    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.start_time + char.start_time

    accent_col = dango_style.get("body", {}).get("1c", "&HFFFFFF&")
    border_col = dango_style.get("body", {}).get("3c", "&H000000&")

    l.text = (
        "{\\an5\\pos(%.3f,%.3f)\\fad(%d,0)\\1c%s\\3c%s\\t(0,%d,\\1c%s\\3c%s)}%s"
        % (
            char.center,
            char.middle,
            line.leadin // 2,
            accent_col,
            border_col,
            line.leadin // 2,
            line.styleref.color1,
            line.styleref.color3,
            char.text,
        )
    )

    io.write_line(l)


@io.track
def main_effect(
    line: Line, char: Char, dango_style: dict[str, dict[str, str | float]]
) -> None:
    l = line.copy()
    l.layer = 6

    l.start_time = line.start_time + char.start_time
    l.end_time = line.start_time + char.end_time

    accent_col = dango_style.get("body", {}).get("1c", "&HFFFFFF&")
    border_col = dango_style.get("body", {}).get("3c", "&H000000&")

    l.text = (
        "{\\an5\\pos(%.3f,%.3f)"
        "\\t(0,%d,0.5,\\1c%s\\3c%s\\fscx125\\fscy125)"
        "\\t(%d,%d,1.5,\\fscx100\\fscy100\\1c%s\\3c%s)}%s"
        % (
            char.center,
            char.middle,
            char.duration // 3,
            accent_col,
            border_col,
            char.duration // 3,
            char.duration,
            line.styleref.color1,
            line.styleref.color3,
            char.text,
        )
    )

    io.write_line(l)


def process_romaji_line(line: Line, l: Line) -> None:
    # Character collection and context setup
    chars = Utils.all_non_empty(line.chars)
    contexts: list[
        tuple[tuple[dict[str, Shape], dict[str, dict[str, str | float]]], Dango]
    ] = []

    # Process each character
    for char in chars:
        fx_name = (getattr(char, "inline_fx", "") or "").strip().lower()

        # Determine variant and config
        if fx_name in VARIANT_LOOKUP and char.syl_char_i == 0:
            name = fx_name
            shape_parts, style_config = VARIANT_LOOKUP[fx_name]
        else:
            name = "base"
            shape_parts, style_config = VARIANT_LOOKUP["base"][0], random.choice(
                VARIANT_BASE_CONFIGS
            )

        # Create leadin and main effects
        leadin_effect(line, char, style_config)
        main_effect(line, char, style_config)

        # Create dango instance
        dango = Dango(
            name=name,
            x=char.left,
            y=char.top,
            current_time=line.start_time + char.end_time,
            shape_parts=shape_parts,
            style_config=style_config,
            line_template=l,
        )

        # Store context
        char_shape = Convert.text_to_shape(char)
        source_context = (
            {"char": char_shape},
            {
                "char": {
                    "1c": char.styleref.color1,
                    "3c": char.styleref.color3,
                    "1a": float(Convert.alpha_ass_to_dec(char.styleref.alpha1)),
                    "3a": float(Convert.alpha_ass_to_dec(char.styleref.alpha3)),
                    "bord": float(char.styleref.outline),
                }
            },
        )
        contexts.append((source_context, dango))

    # Leadout effect
    MORPH_DURATION = 400
    MORPH_EXTRA_TIME = 300

    # Pairing logic
    is_piggy_line = getattr(line, "effect", "").lower() == "piggyback"
    paired = set()

    for i, (curr_context, dango) in enumerate(contexts):
        if i in paired:
            continue

        # Angry-cute tug away pairing
        if dango.name == "angry":
            for j in range(i + 1, min(i + 6, len(contexts))):
                if j not in paired and contexts[j][1].name == "cute":
                    cute = contexts[j][1]
                    dango.morph_from_shapes(
                        *curr_context,
                        MORPH_DURATION + random.randint(0, MORPH_EXTRA_TIME),
                    )
                    cute.morph_from_shapes(
                        *contexts[j][0],
                        MORPH_DURATION + random.randint(0, MORPH_EXTRA_TIME),
                    )
                    dango.tug_away(cute)
                    paired.update([i, j])
                    break

        # Piggyback pairing
        elif is_piggy_line and i + 1 < len(contexts) and i + 1 not in paired:
            dango2 = contexts[i + 1][1]
            dango.morph_from_shapes(*curr_context, MORPH_DURATION, 1)
            dango2.morph_from_shapes(*contexts[i + 1][0], MORPH_DURATION)
            dango.piggyback_onto(dango2)
            paired.update([i, i + 1])

    # Handle solo dangos
    exit_effects = {
        "angry": "exit_furious_dash",
        "cute": "exit_heart_spiral",
        "grandpa": "exit_slow_steps",
        "granny": "exit_slow_steps",
    }
    for i, (curr_context, dango) in enumerate(contexts):
        if i not in paired:
            dango.morph_from_shapes(
                *curr_context, MORPH_DURATION + random.randint(0, MORPH_EXTRA_TIME)
            )
            exit_method = getattr(
                dango, exit_effects.get(dango.name, "exit_jump_down_fall")
            )
            exit_method()


def process_subtitle_line(line: Line, l: Line) -> None:
    l.start_time = line.start_time - line.leadin // 2
    l.end_time = line.end_time + line.leadout // 2

    l.text = "{\\fad(%d,%d)}%s" % (line.leadin // 2, line.leadout // 2, line.text)

    io.write_line(l)


# Main
for line in lines:
    if line.styleref.alignment >= 7:
        process_romaji_line(line, line.copy())
    else:
        process_subtitle_line(line, line.copy())

# Save and open in Aegisub
io.save()
io.open_aegisub()
