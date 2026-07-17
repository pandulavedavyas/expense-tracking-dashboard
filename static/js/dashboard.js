let monthlyChart = null;
let ivChart = null;
let catChart = null;
let savChart = null;

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function openModal(id) {
    document.getElementById(id).classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
    document.body.style.overflow = '';
}

function selectType(btn) {
    btn.parentElement.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('txType').value = btn.dataset.type;
}

function selectEditType(btn) {
    btn.parentElement.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('editTxType').value = btn.dataset.type;
}

function showToast(message, type) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.innerHTML = '<i class="fas fa-' + (type === 'success' ? 'check-circle' : 'exclamation-circle') + '"></i><span>' + message + '</span><button class="toast-close" onclick="this.parentElement.remove()">&times;</button>';
    container.appendChild(toast);
    setTimeout(() => { toast.style.animation = 'toastOut 0.3s ease forwards'; setTimeout(() => toast.remove(), 300); }, 4000);
}

document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', function(e) {
        if (e.target === this) { this.classList.remove('active'); document.body.style.overflow = ''; }
    });
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => {
            m.classList.remove('active');
            document.body.style.overflow = '';
        });
    }
});

const categoryColors = {
    'Food': '#ef4444', 'Shopping': '#f59e0b', 'Bills': '#3b82f6', 'Medical': '#ec4899',
    'Travel': '#8b5cf6', 'Fuel': '#6366f1', 'Education': '#14b8a6', 'Investment': '#10b981',
    'Salary': '#22c55e', 'Entertainment': '#f97316', 'Others': '#6b7280'
};

function fmt(n) {
    return currencySymbol + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function updateCards(dash) {
    document.getElementById('valBalance').textContent = fmt(dash.summary.balance);
    document.getElementById('valIncome').textContent = fmt(dash.summary.total_income);
    document.getElementById('valExpense').textContent = fmt(dash.summary.total_expense);
    document.getElementById('valSavings').textContent = fmt(dash.summary.savings);
}

function updateRecentTransactions(transactions) {
    const el = document.getElementById('recentTransactions');
    if (!transactions || transactions.length === 0) {
        el.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i><p>No transactions yet. Add your first one!</p></div>';
        return;
    }
    el.innerHTML = transactions.map(tx => {
        const icon = categoryIcons[tx.category] || 'fa-ellipsis-h';
        const cls = tx.type === 'income' ? 'tx-income' : 'tx-expense';
        const amtCls = tx.type === 'income' ? 'amount-income' : 'amount-expense';
        const sign = tx.type === 'income' ? '+' : '-';
        return '<div class="transaction-item" data-id="' + tx.id + '">' +
            '<div class="tx-category-icon ' + cls + '"><i class="fas ' + icon + '"></i></div>' +
            '<div class="tx-details"><span class="tx-title">' + tx.title + '</span>' +
            '<span class="tx-meta">' + tx.category + ' &middot; ' + tx.payment_method + ' &middot; ' + tx.date_display + '</span></div>' +
            '<span class="tx-amount ' + amtCls + '">' + sign + fmt(tx.amount) + '</span>' +
            '</div>';
    }).join('');
}

function updateBudget(dash) {
    const el = document.getElementById('budgetSection');
    if (dash.monthly_budget > 0) {
        const pct = Math.min(dash.budget_progress, 100);
        const cls = pct >= 90 ? 'budget-danger' : pct >= 70 ? 'budget-warning' : 'budget-ok';
        el.innerHTML = '<div class="budget-info"><span>' + fmt(dash.summary.total_expense) + ' of ' + fmt(dash.monthly_budget) + '</span>' +
            '<span class="budget-percent">' + Math.round(pct) + '%</span></div>' +
            '<div class="budget-bar"><div class="budget-fill ' + cls + '" style="width:' + pct + '%"></div></div>';
    } else {
        el.innerHTML = '<p class="no-budget">No budget set. Go to Settings to set one.</p>';
    }
}

function updateInsights(insights) {
    const el = document.getElementById('insightsList');
    if (!insights || insights.length === 0) {
        el.innerHTML = '<li><i class="fas fa-info-circle"></i> Add some transactions to see insights.</li>';
        return;
    }
    el.innerHTML = insights.map(i => '<li><i class="fas fa-check-circle"></i> ' + i + '</li>').join('');
}

function updateCharts(dash) {
    const months = dash.yearly.map(d => d.month);
    const expenses = dash.yearly.map(d => d.expense);
    const incomes = dash.yearly.map(d => d.income);
    const savings = dash.yearly.map(d => d.savings);

    if (monthlyChart) monthlyChart.destroy();
    const mCtx = document.getElementById('monthlyExpenseChart');
    if (mCtx) {
        monthlyChart = new Chart(mCtx, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [{ label: 'Expenses', data: expenses, backgroundColor: 'rgba(239,68,68,0.7)', borderColor: '#ef4444', borderWidth: 1, borderRadius: 6 }]
            },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { callback: v => currencySymbol + v.toLocaleString() } } } }
        });
    }

    if (ivChart) ivChart.destroy();
    const ivCtx = document.getElementById('incomeVsExpenseChart');
    if (ivCtx) {
        ivChart = new Chart(ivCtx, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [
                    { label: 'Income', data: incomes, backgroundColor: 'rgba(16,185,129,0.7)', borderColor: '#10b981', borderWidth: 1, borderRadius: 6 },
                    { label: 'Expense', data: expenses, backgroundColor: 'rgba(239,68,68,0.7)', borderColor: '#ef4444', borderWidth: 1, borderRadius: 6 }
                ]
            },
            options: { responsive: true, maintainAspectRatio: true, scales: { y: { beginAtZero: true, ticks: { callback: v => currencySymbol + v.toLocaleString() } } } }
        });
    }

    if (catChart) catChart.destroy();
    const cCtx = document.getElementById('categoryChart');
    const catLabels = Object.keys(dash.categories.categories);
    const catData = Object.values(dash.categories.categories);
    if (cCtx && catLabels.length > 0) {
        catChart = new Chart(cCtx, {
            type: 'doughnut',
            data: {
                labels: catLabels,
                datasets: [{ data: catData, backgroundColor: catLabels.map(l => categoryColors[l] || '#6b7280'), borderWidth: 2, borderColor: '#fff' }]
            },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true, pointStyle: 'circle' } } } }
        });
    } else if (cCtx) {
        catChart = new Chart(cCtx, {
            type: 'doughnut',
            data: { labels: ['No Data'], datasets: [{ data: [1], backgroundColor: ['#e2e8f0'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } } }
        });
    }

    if (savChart) savChart.destroy();
    const sCtx = document.getElementById('savingsChart');
    if (sCtx) {
        savChart = new Chart(sCtx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [{ label: 'Savings', data: savings, borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.1)', fill: true, tension: 0.4, pointBackgroundColor: '#6366f1', pointRadius: 5 }]
            },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } }, scales: { y: { ticks: { callback: v => currencySymbol + v.toLocaleString() } } } }
        });
    }
}

async function loadDashboard(filter) {
    filter = filter || 'this_month';
    try {
        const resp = await fetch('/api/dashboard-data?filter=' + filter);
        const dash = await resp.json();
        updateCards(dash);
        updateRecentTransactions(dash.recent_transactions);
        updateBudget(dash);
        updateInsights(dash.insights);
        updateCharts(dash);
    } catch (err) {
        console.error('Failed to load dashboard:', err);
    }
}

async function handleAddTransaction(e) {
    e.preventDefault();
    const btn = document.getElementById('addTxBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    const payload = {
        title: document.getElementById('txTitle').value,
        amount: parseFloat(document.getElementById('txAmount').value),
        type: document.getElementById('txType').value,
        category: document.getElementById('txCategory').value,
        payment_method: document.getElementById('txPayment').value,
        date: document.getElementById('txDate').value,
        description: document.getElementById('txNotes').value
    };

    try {
        const resp = await fetch('/api/transactions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.success) {
            showToast(data.message, 'success');
            document.getElementById('addTxForm').reset();
            document.getElementById('txType').value = 'expense';
            document.querySelectorAll('#addTransactionModal .type-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.type === 'expense');
            });
            document.getElementById('txDate').value = new Date().toISOString().split('T')[0];
            closeModal('addTransactionModal');
            if (data.dashboard) {
                updateCards(data.dashboard);
                updateRecentTransactions(data.dashboard.recent_transactions);
                updateBudget(data.dashboard);
                updateInsights(data.dashboard.insights);
                updateCharts(data.dashboard);
            } else {
                loadDashboard();
            }
        } else {
            showToast(data.error || 'Failed to add transaction', 'error');
        }
    } catch (err) {
        showToast('Network error. Please try again.', 'error');
        console.error(err);
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-plus"></i> Save Transaction';
    return false;
}

async function handleEditTransaction(e) {
    e.preventDefault();
    const txId = document.getElementById('editTxId').value;
    const btn = document.getElementById('editTxBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    const payload = {
        title: document.getElementById('editTxTitle').value,
        amount: parseFloat(document.getElementById('editTxAmount').value),
        type: document.getElementById('editTxType').value,
        category: document.getElementById('editTxCategory').value,
        payment_method: document.getElementById('editTxPayment').value,
        date: document.getElementById('editTxDate').value,
        description: document.getElementById('editTxNotes').value
    };

    try {
        const resp = await fetch('/api/transactions/' + txId, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.success) {
            showToast(data.message, 'success');
            closeModal('editTransactionModal');
            if (data.dashboard) {
                updateCards(data.dashboard);
                updateRecentTransactions(data.dashboard.recent_transactions);
                updateBudget(data.dashboard);
                updateInsights(data.dashboard.insights);
                updateCharts(data.dashboard);
            } else {
                loadDashboard();
            }
        } else {
            showToast(data.error || 'Failed to update', 'error');
        }
    } catch (err) {
        showToast('Network error.', 'error');
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
    return false;
}

async function deleteTransaction(txId) {
    if (!confirm('Delete this transaction?')) return;
    try {
        const resp = await fetch('/api/transactions/' + txId, { method: 'DELETE' });
        const data = await resp.json();
        if (data.success) {
            showToast(data.message, 'success');
            if (data.dashboard) {
                updateCards(data.dashboard);
                updateRecentTransactions(data.dashboard.recent_transactions);
                updateBudget(data.dashboard);
                updateInsights(data.dashboard.insights);
                updateCharts(data.dashboard);
            } else {
                loadDashboard();
            }
        }
    } catch (err) {
        showToast('Failed to delete.', 'error');
    }
}

function openEditModal(txId) {
    fetch('/api/transactions?search=&type=&category=&payment=&filter=this_month&sort=date_desc')
        .then(r => r.json())
        .then(data => {
            const tx = data.transactions.find(t => t.id === txId);
            if (!tx) return fetch('/api/transactions?filter=this_year&sort=date_desc').then(r => r.json()).then(d => d.transactions.find(t => t.id === txId));
            return tx;
        })
        .then(tx => {
            if (!tx) return;
            document.getElementById('editTxId').value = tx.id;
            document.getElementById('editTxTitle').value = tx.title;
            document.getElementById('editTxAmount').value = tx.amount;
            document.getElementById('editTxDate').value = tx.date;
            document.getElementById('editTxCategory').value = tx.category;
            document.getElementById('editTxPayment').value = tx.payment_method;
            document.getElementById('editTxNotes').value = tx.description;
            document.getElementById('editTxType').value = tx.type;
            document.querySelectorAll('#editTransactionModal .type-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.type === tx.type);
            });
            openModal('editTransactionModal');
        });
}

document.addEventListener('DOMContentLoaded', function() {
    loadDashboard('this_month');
});
