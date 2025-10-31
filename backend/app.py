from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 数据库配置
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'schedule.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 任务数据模型
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    start_time = db.Column(db.String(5), nullable=False)  # HH:MM
    duration = db.Column(db.Integer, nullable=False)  # 分钟数
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'start_time': self.start_time,
            'duration': self.duration,
            'title': self.title,
            'location': self.location,
            'description': self.description
        }

# 初始化数据库
with app.app_context():
    db.create_all()

# API路由

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务或指定日期范围的任务"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date and end_date:
        tasks = Task.query.filter(Task.date >= start_date, Task.date <= end_date).all()
    else:
        tasks = Task.query.all()
    
    return jsonify([task.to_dict() for task in tasks])

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取单个任务详情"""
    task = Task.query.get_or_404(task_id)
    return jsonify(task.to_dict())

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    data = request.json
    
    task = Task(
        date=data['date'],
        start_time=data['start_time'],
        duration=data.get('duration', 45),
        title=data['title'],
        location=data.get('location', ''),
        description=data.get('description', '')
    )
    
    db.session.add(task)
    db.session.commit()
    
    return jsonify(task.to_dict()), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    task = Task.query.get_or_404(task_id)
    data = request.json
    
    task.date = data.get('date', task.date)
    task.start_time = data.get('start_time', task.start_time)
    task.duration = data.get('duration', task.duration)
    task.title = data.get('title', task.title)
    task.location = data.get('location', task.location)
    task.description = data.get('description', task.description)
    
    db.session.commit()
    
    return jsonify(task.to_dict())

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': 'Task deleted successfully'}), 200

@app.route('/api/tasks/merge', methods=['POST'])
def merge_tasks():
    """合并多个任务"""
    data = request.json
    task_ids = data.get('task_ids', [])
    
    if len(task_ids) < 2:
        return jsonify({'error': 'At least 2 tasks required'}), 400
    
    tasks = Task.query.filter(Task.id.in_(task_ids)).all()
    
    if len(tasks) != len(task_ids):
        return jsonify({'error': 'Some tasks not found'}), 404
    
    # 按时间排序
    tasks.sort(key=lambda t: (t.date, t.start_time))
    
    # 计算总时长
    first_task = tasks[0]
    total_duration = sum(task.duration for task in tasks)
    
    # 更新第一个任务
    first_task.duration = total_duration
    first_task.title = data.get('title', first_task.title)
    first_task.location = data.get('location', first_task.location)
    first_task.description = data.get('description', first_task.description)
    
    # 删除其他任务
    for task in tasks[1:]:
        db.session.delete(task)
    
    db.session.commit()
    
    return jsonify(first_task.to_dict())

@app.route('/api/tasks/<int:task_id>/split', methods=['POST'])
def split_task(task_id):
    """拆分任务"""
    task = Task.query.get_or_404(task_id)
    data = request.json
    split_count = data.get('split_count', 2)
    
    if split_count < 2:
        return jsonify({'error': 'Split count must be at least 2'}), 400
    
    duration_per_task = task.duration // split_count
    
    # 保留原任务并修改时长
    task.duration = duration_per_task
    
    # 创建新的拆分任务
    new_tasks = []
    current_time = datetime.strptime(task.start_time, '%H:%M')
    
    for i in range(1, split_count):
        current_time += timedelta(minutes=duration_per_task + 10)  # 加上10分钟休息
        
        new_task = Task(
            date=task.date,
            start_time=current_time.strftime('%H:%M'),
            duration=duration_per_task,
            title=f"{task.title} ({i+1})",
            location=task.location,
            description=task.description
        )
        db.session.add(new_task)
        new_tasks.append(new_task)
    
    db.session.commit()
    
    return jsonify({
        'original': task.to_dict(),
        'new_tasks': [t.to_dict() for t in new_tasks]
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
