// API配置
const API_BASE_URL = 'http://localhost:5000/api';

// 全局状态
let currentWeekStart = null;
let selectedCells = [];
let allTasks = [];

// 时间配置：8:00-10:55，每格45分钟，间隔10分钟
const TIME_SLOTS = [
    { start: '08:00', end: '08:45' },
    { start: '08:55', end: '09:40' },
    { start: '09:50', end: '10:35' },
    { start: '10:45', end: '10:55' }  // 最后一个时间段较短
];

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
});

function initializeApp() {
    // 设置当前周为本周
    const today = new Date();
    currentWeekStart = getWeekStart(today);
    
    // 渲染界面
    renderSchedule();
    loadTasks();
}

function setupEventListeners() {
    // 导航按钮
    document.getElementById('prevWeek').addEventListener('click', () => {
        currentWeekStart.setDate(currentWeekStart.getDate() - 7);
        renderSchedule();
        loadTasks();
    });
    
    document.getElementById('nextWeek').addEventListener('click', () => {
        currentWeekStart.setDate(currentWeekStart.getDate() + 7);
        renderSchedule();
        loadTasks();
    });
    
    document.getElementById('todayBtn').addEventListener('click', () => {
        currentWeekStart = getWeekStart(new Date());
        renderSchedule();
        loadTasks();
    });
    
    document.getElementById('datePicker').addEventListener('change', (e) => {
        const selectedDate = new Date(e.target.value);
        currentWeekStart = getWeekStart(selectedDate);
        renderSchedule();
        loadTasks();
    });
    
    // 模态框事件
    const modal = document.getElementById('taskModal');
    const closeBtn = document.querySelector('.close');
    const cancelBtn = document.querySelector('.cancel-btn');
    
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        clearSelection();
    });
    
    cancelBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        clearSelection();
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
            clearSelection();
        }
    });
    
    // 表单提交
    document.getElementById('taskForm').addEventListener('submit', handleTaskSubmit);
    
    // 删除按钮
    document.getElementById('deleteBtn').addEventListener('click', handleTaskDelete);
    
    // 拆分按钮
    document.getElementById('splitBtn').addEventListener('click', handleTaskSplit);
}

// 获取一周的开始日期（周一）
function getWeekStart(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
}

// 渲染课程表
function renderSchedule() {
    const dateHeader = document.getElementById('dateHeader');
    const scheduleBody = document.getElementById('scheduleBody');
    
    // 清空现有内容
    dateHeader.innerHTML = '<th class="time-column">时间</th>';
    scheduleBody.innerHTML = '';
    
    // 生成日期列标题
    const dates = [];
    for (let i = 0; i < 7; i++) {
        const date = new Date(currentWeekStart);
        date.setDate(date.getDate() + i);
        dates.push(date);
        
        const th = document.createElement('th');
        const weekDay = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][date.getDay()];
        const isToday = isDateToday(date);
        const isWeekend = date.getDay() === 0 || date.getDay() === 6;
        
        th.innerHTML = `
            ${weekDay}<br>
            ${formatDate(date, 'MM/DD')}
            ${isToday ? ' 🔵' : ''}
        `;
        
        if (isWeekend) {
            th.classList.add('weekend-column');
        }
        if (isToday) {
            th.classList.add('today-column');
        }
        
        dateHeader.appendChild(th);
    }
    
    // 生成时间格
    TIME_SLOTS.forEach((slot, slotIndex) => {
        const tr = document.createElement('tr');
        
        // 时间列
        const timeCell = document.createElement('td');
        timeCell.className = 'time-cell';
        timeCell.textContent = `${slot.start}\n-\n${slot.end}`;
        tr.appendChild(timeCell);
        
        // 每天的格子
        dates.forEach((date, dayIndex) => {
            const td = document.createElement('td');
            td.className = 'schedule-cell';
            td.dataset.date = formatDate(date, 'YYYY-MM-DD');
            td.dataset.time = slot.start;
            td.dataset.slotIndex = slotIndex;
            td.dataset.dayIndex = dayIndex;
            
            const isWeekend = date.getDay() === 0 || date.getDay() === 6;
            const isToday = isDateToday(date);
            
            if (isWeekend) {
                td.classList.add('weekend-column');
            }
            if (isToday) {
                td.classList.add('today-column');
            }
            
            // 添加点击事件
            td.addEventListener('click', (e) => handleCellClick(e, td));
            
            tr.appendChild(td);
        });
        
        scheduleBody.appendChild(tr);
    });
    
    // 更新周信息显示
    const weekEnd = new Date(currentWeekStart);
    weekEnd.setDate(weekEnd.getDate() + 6);
    document.getElementById('weekInfo').textContent = 
        `${formatDate(currentWeekStart, 'YYYY/MM/DD')} - ${formatDate(weekEnd, 'YYYY/MM/DD')}`;
}

// 处理单元格点击
function handleCellClick(e, cell) {
    // 如果单元格已有任务，编辑任务
    if (cell.classList.contains('has-task')) {
        const taskId = parseInt(cell.dataset.taskId);
        editTask(taskId);
        return;
    }
    
    // 多选模式（按住Ctrl或Shift）
    if (e.ctrlKey || e.shiftKey) {
        if (cell.classList.contains('selected')) {
            cell.classList.remove('selected');
            selectedCells = selectedCells.filter(c => c !== cell);
        } else {
            cell.classList.add('selected');
            selectedCells.push(cell);
        }
    } else {
        // 单选模式
        clearSelection();
        cell.classList.add('selected');
        selectedCells = [cell];
        
        // 立即打开创建任务对话框
        openTaskModal();
    }
}

// 清除选择
function clearSelection() {
    selectedCells.forEach(cell => cell.classList.remove('selected'));
    selectedCells = [];
}

// 打开任务模态框
function openTaskModal(task = null) {
    const modal = document.getElementById('taskModal');
    const form = document.getElementById('taskForm');
    
    form.reset();
    
    if (task) {
        // 编辑模式
        document.getElementById('modalTitle').textContent = '编辑任务';
        document.getElementById('taskId').value = task.id;
        document.getElementById('taskDate').value = task.date;
        document.getElementById('taskStartTime').value = task.start_time;
        document.getElementById('taskDuration').value = task.duration;
        document.getElementById('taskTitle').value = task.title;
        document.getElementById('taskLocation').value = task.location || '';
        document.getElementById('taskDescription').value = task.description || '';
        
        document.getElementById('displayDate').textContent = task.date;
        document.getElementById('displayTime').textContent = task.start_time;
        document.getElementById('displayDuration').textContent = task.duration;
        
        document.getElementById('deleteBtn').style.display = 'block';
        document.getElementById('splitBtn').style.display = 'block';
    } else {
        // 创建模式
        document.getElementById('modalTitle').textContent = '新建任务';
        
        if (selectedCells.length > 0) {
            const firstCell = selectedCells[0];
            const date = firstCell.dataset.date;
            const time = firstCell.dataset.time;
            const duration = calculateDuration();
            
            document.getElementById('taskDate').value = date;
            document.getElementById('taskStartTime').value = time;
            document.getElementById('taskDuration').value = duration;
            
            document.getElementById('displayDate').textContent = date;
            document.getElementById('displayTime').textContent = time;
            document.getElementById('displayDuration').textContent = duration;
        }
        
        document.getElementById('deleteBtn').style.display = 'none';
        document.getElementById('splitBtn').style.display = 'none';
    }
    
    modal.style.display = 'block';
}

// 计算选中单元格的总时长
function calculateDuration() {
    if (selectedCells.length === 0) return 45;
    
    // 检查是否为连续选择
    const sorted = selectedCells.sort((a, b) => {
        const aDate = a.dataset.date;
        const bDate = b.dataset.date;
        const aTime = a.dataset.time;
        const bTime = b.dataset.time;
        
        if (aDate !== bDate) return aDate.localeCompare(bDate);
        return aTime.localeCompare(bTime);
    });
    
    // 计算总时长
    return selectedCells.length * 45 + (selectedCells.length - 1) * 10;
}

// 编辑任务
function editTask(taskId) {
    const task = allTasks.find(t => t.id === taskId);
    if (task) {
        openTaskModal(task);
    }
}

// 处理任务提交
async function handleTaskSubmit(e) {
    e.preventDefault();
    
    const taskId = document.getElementById('taskId').value;
    const taskData = {
        date: document.getElementById('taskDate').value,
        start_time: document.getElementById('taskStartTime').value,
        duration: parseInt(document.getElementById('taskDuration').value),
        title: document.getElementById('taskTitle').value,
        location: document.getElementById('taskLocation').value,
        description: document.getElementById('taskDescription').value
    };
    
    try {
        let response;
        if (taskId) {
            // 更新任务
            response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });
        } else {
            // 创建任务
            response = await fetch(`${API_BASE_URL}/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });
        }
        
        if (response.ok) {
            document.getElementById('taskModal').style.display = 'none';
            clearSelection();
            loadTasks();
        } else {
            alert('操作失败，请重试');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('网络错误，请检查后端服务是否运行');
    }
}

// 删除任务
async function handleTaskDelete() {
    const taskId = document.getElementById('taskId').value;
    
    if (!confirm('确定要删除这个任务吗？')) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            document.getElementById('taskModal').style.display = 'none';
            loadTasks();
        } else {
            alert('删除失败，请重试');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('网络错误');
    }
}

// 拆分任务
async function handleTaskSplit() {
    const taskId = document.getElementById('taskId').value;
    const splitCount = prompt('请输入要拆分成几个任务（2-4）：', '2');
    
    if (!splitCount || splitCount < 2 || splitCount > 4) {
        alert('拆分数量必须在2-4之间');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/split`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ split_count: parseInt(splitCount) })
        });
        
        if (response.ok) {
            document.getElementById('taskModal').style.display = 'none';
            loadTasks();
        } else {
            alert('拆分失败，请重试');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('网络错误');
    }
}

// 加载任务数据
async function loadTasks() {
    const weekEnd = new Date(currentWeekStart);
    weekEnd.setDate(weekEnd.getDate() + 6);
    
    const startDate = formatDate(currentWeekStart, 'YYYY-MM-DD');
    const endDate = formatDate(weekEnd, 'YYYY-MM-DD');
    
    try {
        const response = await fetch(`${API_BASE_URL}/tasks?start_date=${startDate}&end_date=${endDate}`);
        
        if (response.ok) {
            allTasks = await response.json();
            renderTasks();
        } else {
            console.error('Failed to load tasks');
        }
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

// 渲染任务到表格
function renderTasks() {
    // 清除所有任务显示
    document.querySelectorAll('.schedule-cell').forEach(cell => {
        cell.classList.remove('has-task');
        cell.innerHTML = '';
        delete cell.dataset.taskId;
    });
    
    // 渲染每个任务
    allTasks.forEach(task => {
        const cell = document.querySelector(
            `.schedule-cell[data-date="${task.date}"][data-time="${task.start_time}"]`
        );
        
        if (cell) {
            cell.classList.add('has-task');
            cell.dataset.taskId = task.id;
            
            // 计算任务跨越的格子数
            const slots = Math.ceil(task.duration / 55); // 45分钟 + 10分钟休息
            
            if (slots > 1) {
                // 合并单元格效果
                cell.rowSpan = slots;
                
                // 隐藏被合并的单元格
                let currentCell = cell;
                for (let i = 1; i < slots; i++) {
                    const nextRow = currentCell.parentElement.nextElementSibling;
                    if (nextRow) {
                        const nextCell = nextRow.children[parseInt(cell.dataset.dayIndex) + 1];
                        if (nextCell) {
                            nextCell.style.display = 'none';
                        }
                    }
                    currentCell = currentCell.parentElement.nextElementSibling?.children[parseInt(cell.dataset.dayIndex) + 1];
                }
            }
            
            cell.innerHTML = `
                <div class="task-content">
                    <div><strong>${task.title}</strong></div>
                    ${task.location ? `<div>📍 ${task.location}</div>` : ''}
                    <div class="task-time">${task.start_time}</div>
                </div>
            `;
        }
    });
}

// 日期格式化
function formatDate(date, format) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day);
}

// 判断是否为今天
function isDateToday(date) {
    const today = new Date();
    return date.getDate() === today.getDate() &&
           date.getMonth() === today.getMonth() &&
           date.getFullYear() === today.getFullYear();
}
