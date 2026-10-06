import random
import pygame
from game.color_button import ColorButton
import math
import array

def make_tone(frequency, duration_ms=250, volume=0.4):
    """Build a short sine-wave beep as a pygame Sound (no audio files needed)."""
    sample_rate, _, channels = pygame.mixer.get_init()
    total = int(sample_rate * duration_ms / 1000)
    fade = int(sample_rate * 0.02)  

    samples = array.array("h")
    for i in range(total):
        envelope = min(1.0, i / fade, (total - i) / fade)
        value = int(32767 * volume * envelope * math.sin(2 * math.pi * frequency * i / sample_rate))
        for _ in range(channels):
            samples.append(value)

    return pygame.mixer.Sound(buffer=samples.tobytes())


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        pad_size = 130
        gap = 24
        start_x = width // 2 - pad_size - (gap // 2)
        start_y = 150

        self.buttons = [
            ColorButton(0, pygame.Rect(start_x, start_y, pad_size, pad_size), (110, 20, 20), (255, 50, 50)),                      # Red
            ColorButton(1, pygame.Rect(start_x + pad_size + gap, start_y, pad_size, pad_size), (15, 60, 150), (40, 170, 255)),   # Blue
            ColorButton(2, pygame.Rect(start_x, start_y + pad_size + gap, pad_size, pad_size), (15, 100, 30), (50, 255, 90)),    # Green
            ColorButton(3, pygame.Rect(start_x + pad_size + gap, start_y + pad_size + gap, pad_size, pad_size), (140, 110, 10), (255, 235, 40)), # Yellow
        ]
        self.sounds = [make_tone(freq) for freq in (262, 330, 392, 523)]
        

        self.sequence = []
        self.player_input = []
        self.score = 0

        self.state = "WATCH"
        self.showing_step = 0
        self.step_start_time = 0
        self.base_flash_duration = 450
        self.base_pause_duration = 200
        self.min_flash_duration = 120
        self.min_pause_duration = 60
        self.flash_speedup_per_round = 35
        self.pause_speedup_per_round = 15

        self.flash_duration = self.base_flash_duration
        self.pause_duration = self.base_pause_duration
        self.is_flashing = False

        self.player_lit_button = None
        self.player_lit_start = 0
        self.player_flash_duration = 150

        self.turn_base_time = 3000
        self.turn_time_per_step = 1000
        self.turn_start_time = 0
        self.turn_time_limit = 0
        self.game_over_reason = ""

        self.font_title = pygame.font.SysFont(None, 40)
        self.font_medium = pygame.font.SysFont(None, 28)

        self.start_next_round()

    def update_playback_speed(self):
        round_number = len(self.sequence)  
        steps_faster = round_number - 1

        self.flash_duration = max(
        self.min_flash_duration,
        self.base_flash_duration - steps_faster * self.flash_speedup_per_round,
    )
        self.pause_duration = max(
        self.min_pause_duration,
        self.base_pause_duration - steps_faster * self.pause_speedup_per_round,
    )

    def start_next_round(self):
        new_color = random.randint(0, 3)

        self.sequence.append(new_color)
        self.update_playback_speed()
        
        self.player_input.clear()
        self.state = "WATCH"
        self.showing_step = 0
        self.step_start_time = pygame.time.get_ticks()
        self.is_flashing = True
        self.buttons[self.sequence[0]].is_lit = True
        self.sounds[self.sequence[0]].play()
        
    def update(self):
        now = pygame.time.get_ticks()

        if self.player_lit_button is not None:
            if now - self.player_lit_start >= self.player_flash_duration:
                self.player_lit_button.is_lit = False
                self.player_lit_button = None

        if self.state == "WATCH":
            current_btn_id = self.sequence[self.showing_step]

            if self.is_flashing:
                if now - self.step_start_time >= self.flash_duration:
                    self.buttons[current_btn_id].is_lit = False
                    self.is_flashing = False
                    self.step_start_time = now
            else:
                if now - self.step_start_time >= self.pause_duration:
                    self.showing_step += 1
                    if self.showing_step < len(self.sequence):
                        next_id = self.sequence[self.showing_step]
                        self.buttons[next_id].is_lit = True
                        self.sounds[next_id].play()
                        self.is_flashing = True
                        self.step_start_time = now
                    else:
                        self.state = "PLAYER_TURN"
                        self.turn_start_time = now
                        self.turn_time_limit = self.turn_base_time + self.turn_time_per_step * len(self.sequence)

        if self.state == "PLAYER_TURN":
            if now - self.turn_start_time >= self.turn_time_limit:
                self.game_over_reason = "TIME'S UP! GAME OVER"
                self.state = "GAME_OVER"

    def handle_event(self, event):
        if self.state == "GAME_OVER":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset()
            return

        if self.state == "PLAYER_TURN" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn.contains(event.pos):
                    btn.is_lit = True
                    self.sounds[btn.color_id].play()
                    self.player_lit_button = btn
                    self.player_lit_start = pygame.time.get_ticks()

                    self.register_player_click(btn.color_id)
                    break

    def register_player_click(self, color_id):
        self.player_input.append(color_id)
        current_idx = len(self.player_input) - 1

        if self.player_input[current_idx] != self.sequence[current_idx]:
            self.game_over_reason = "WRONG PATTERN! GAME OVER"
            self.state = "GAME_OVER"
            return

        if len(self.player_input) == len(self.sequence):
            self.score += 1
            self.start_next_round()

    def reset(self):
        self.sequence.clear()
        self.player_input.clear()
        self.score = 0
        for btn in self.buttons:
            btn.is_lit = False
        self.player_lit_button = None
        self.start_next_round()

    def render(self, screen):
        screen.fill((22, 24, 30))

        title_surf = self.font_title.render("Memory Pattern Arena", True, (245, 245, 245))
        screen.blit(title_surf, (self.width // 2 - title_surf.get_width() // 2, 20))

        score_surf = self.font_medium.render(f"Score: {self.score}", True, (255, 220, 80))
        screen.blit(score_surf, (self.width // 2 - score_surf.get_width() // 2, 60))

        status_text = "Watch the pattern..." if self.state == "WATCH" else "Your turn: Click the pattern!"
        status_color = (190, 195, 205) if self.state == "WATCH" else (80, 240, 130)
        status_surf = self.font_medium.render(status_text, True, status_color)
        screen.blit(status_surf, (self.width // 2 - status_surf.get_width() // 2, 95))

        for btn in self.buttons:
            btn.render(screen)

        if self.state == "PLAYER_TURN":
            now = pygame.time.get_ticks()
            remaining = max(0, self.turn_time_limit - (now - self.turn_start_time))
            fraction = remaining / self.turn_time_limit

            bar_w, bar_h = 300, 18
            bar_x = self.width // 2 - bar_w // 2
            bar_y = 460

            if fraction > 0.5:
                bar_color = (80, 240, 130)
            elif fraction > 0.25:
                bar_color = (255, 220, 80)
            else:
                bar_color = (240, 70, 70)

            pygame.draw.rect(screen, (45, 48, 58), (bar_x, bar_y, bar_w, bar_h), border_radius=9)
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, int(bar_w * fraction), bar_h), border_radius=9)

        if self.state == "GAME_OVER":
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))

            over_surf = self.font_title.render(self.game_over_reason, True, (240, 70, 70))
            screen.blit(over_surf, (self.width // 2 - over_surf.get_width() // 2, self.height // 2 - 40))

            final_score_surf = self.font_medium.render(f"Final Score: {self.score}", True, (255, 255, 255))
            screen.blit(final_score_surf, (self.width // 2 - final_score_surf.get_width() // 2, self.height // 2 + 10))

            restart_surf = self.font_medium.render("Press [R] to Play Again", True, (200, 200, 200))
            screen.blit(restart_surf, (self.width // 2 - restart_surf.get_width() // 2, self.height // 2 + 50))
