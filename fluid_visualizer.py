# fluid_visualizer.py

from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import QTimer
import moderngl
import numpy as np

class FluidVisualizer(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None
        self.program = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)  # ~60 FPS
        self.fft_data = np.zeros(64)

    def initializeGL(self):
        self.ctx = moderngl.create_context()
        vertex_shader = """
        #version 330
        in vec2 in_vert;
        void main() {
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
        """
        fragment_shader = """
        #version 330
        out vec4 fragColor;
        uniform float time;
        uniform float fft[64];
        void main() {
            vec2 uv = gl_FragCoord.xy / vec2(800.0, 600.0);
            float sum = 0.0;
            for (int i = 0; i < 64; i++) {
                sum += fft[i] * exp(-100.0 * distance(uv, vec2(float(i)/64.0, 0.5)));
            }
            float c = smoothstep(0.0, 0.2, sum);
            fragColor = vec4(vec3(c), 1.0);
        }
        """
        self.program = self.ctx.program(
            vertex_shader=vertex_shader,
            fragment_shader=fragment_shader,
        )
        vertices = np.array([
            -1.0, -1.0,  1.0, -1.0,
            -1.0,  1.0,  1.0,  1.0,
        ], dtype='f4')
        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.vao = self.ctx.simple_vertex_array(self.program, self.vbo, 'in_vert')

    def paintGL(self):
        if not self.ctx:
            return
        self.ctx.clear(0.0, 0.0, 0.0)
        self.program['time'] = self.timer.remainingTime() / 1000.0
        self.program['fft'] = self.fft_data.tolist()
        self.vao.render(moderngl.TRIANGLE_STRIP)

    def update_fft(self, fft_array):
        # Pass 64 normalized values
        self.fft_data = np.clip(np.array(fft_array), 0, 1)
