// Extract data from Django template
const category_wise_data = data.category_wise_data;
const savings = data.savings;
const year_wise_data = data.year_wise_data;
const category_wise_month = data.category_wise_month;
const monthly_cash_flow = data.monthly_cash_flow;
const weekly_spending = data.weekly_spending;
const top_expenses = data.top_expenses;
const savings_rate = data.savings_rate;
const income_sources = data.income_sources;

// ============================================================================
// Loading States - Show shimmer on all chart containers initially
// ============================================================================
document.addEventListener('DOMContentLoaded', function () {
  // Add loading class to all chart containers
  document.querySelectorAll('.card-body canvas').forEach(canvas => {
    canvas.parentElement.classList.add('loading');
  });

  // Remove loading after charts are rendered (triggered at end of file)
  window.chartsLoaded = false;
});

// Function to remove all loading states
function removeLoadingStates() {
  setTimeout(() => {
    document.querySelectorAll('.card-body.loading').forEach(body => {
      body.classList.remove('loading');
    });
    window.chartsLoaded = true;
  }, 300);  // Small delay for smooth transition
}

// ============================================================================
// Empty State Handler - Show helpful messages when no data
// ============================================================================
function showEmptyState(canvasId, message, icon = 'fa-inbox') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const parent = canvas.parentElement;
  parent.classList.remove('loading');
  parent.innerHTML = `
    <div class="text-center py-5 text-muted">
      <i class="fa-solid ${icon} fa-3x mb-3" style="opacity: 0.3;"></i>
      <p class="mb-0">${message}</p>
    </div>
  `;
}


// Color palette — dark theme
const colors = {
  income:  '#4ade80',
  expense: '#f87171',
  savings: '#60a5fa',
  primary: '#c9a84c',
  primaryLight: 'rgba(201,168,76,0.15)',
  grid: 'rgba(255,255,255,0.06)',
  tick: 'rgba(255,255,255,0.45)',
  legend: 'rgba(255,255,255,0.6)',
  categories: [
    '#f87171', '#4ade80', '#a78bfa', '#fbbf24', '#34d399',
    '#fb923c', '#60a5fa', '#e879f9', '#f472b6', '#c9a84c'
  ]
};

// Common chart options
const commonOptions = {
  responsive: true,
  maintainAspectRatio: true,
  interaction: {
    intersect: false,
    mode: 'index'
  },
  animation: {
    duration: 750,
    easing: 'easeInOutQuart'
  }
};

// Currency formatter for tooltips
const currencyFormatter = {
  callbacks: {
    label: function (context) {
      let label = context.dataset.label || '';
      if (label) {
        label += ': ';
      }
      if (context.parsed.y !== null || context.parsed !== null) {
        const value = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
        label += '₹' + value.toLocaleString('en-IN', {
          minimumFractionDigits: 0,
          maximumFractionDigits: 0
        });
      }
      return label;
    }
  }
};

// 1. Cash Flow Trend Chart (Large Hero Chart)
new Chart(document.getElementById('cashFlowChart'), {
  type: 'line',
  data: {
    labels: monthly_cash_flow.labels.reverse(),
    datasets: [
      {
        label: 'Income',
        data: monthly_cash_flow.income.reverse(),
        borderColor: colors.income,
        backgroundColor: 'transparent',
        borderWidth: 3,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: colors.income,
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      },
      {
        label: 'Expense',
        data: monthly_cash_flow.expense.reverse(),
        borderColor: colors.expense,
        backgroundColor: 'transparent',
        borderWidth: 3,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: colors.expense,
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      },
      {
        label: 'Net Savings',
        data: monthly_cash_flow.savings.reverse(),
        borderColor: colors.savings,
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: colors.savings,
        pointBorderColor: '#fff',
        pointBorderWidth: 2
      }
    ]
  },
  options: {
    ...commonOptions,
    aspectRatio: window.innerWidth < 768 ? 1.6 : 2,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          color: colors.legend,
          font: { size: 12 }
        }
      },
      tooltip: currencyFormatter
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          color: colors.tick,
          callback: function (value) {
            return '₹' + value.toLocaleString('en-IN');
          }
        },
        grid: { color: colors.grid }
      },
      x: {
        ticks: { color: colors.tick },
        grid: { display: false }
      }
    }
  }
});

// 2. Category-wise Expense Distribution (Pie Chart) - Mobile Responsive
new Chart(document.getElementById('expenseCategoryChart'), {
  type: 'pie',
  data: {
    labels: Object.keys(category_wise_data),
    datasets: [{
      label: 'Category',
      data: Object.values(category_wise_data),
      backgroundColor: colors.categories,
      borderWidth: 2,
      borderColor: '#1a1917'
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 1.5,
    plugins: {
      legend: {
        position: window.innerWidth < 768 ? 'bottom' : 'right',
        labels: {
          boxWidth: 12,
          padding: 8,
          color: colors.legend,
          font: {
            size: window.innerWidth < 768 ? 9 : 11
          },
          generateLabels: function (chart) {
            const d = chart.data;
            if (d.labels.length && d.datasets.length) {
              return d.labels.map((label, i) => {
                const value = d.datasets[0].data[i];
                const fv = '₹' + (value / 1000).toFixed(1) + 'k';
                return {
                  text: window.innerWidth < 768 ? label.substring(0, 10) : `${label}: ${fv}`,
                  fillStyle: d.datasets[0].backgroundColor[i],
                  hidden: false,
                  index: i
                };
              });
            }
            return [];
          }
        }
      },
      tooltip: currencyFormatter
    }
  }
});

// 6. Weekly Spending Trend
new Chart(document.getElementById('weeklySpendingChart'), {
  type: 'line',
  data: {
    labels: weekly_spending.labels,
    datasets: [{
      label: 'Daily Expense',
      data: weekly_spending.amounts,
      borderColor: '#f59e0b',
      backgroundColor: 'rgba(245, 158, 11, 0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4,
      pointBackgroundColor: '#f59e0b',
      pointBorderColor: '#fff',
      pointBorderWidth: 2
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: false
      },
      tooltip: currencyFormatter
    },
    scales: {
      y: {
        beginAtZero: true,
        position: 'right',
        ticks: {
          color: colors.tick,
          callback: function (value) {
            return '₹' + (value / 1000).toFixed(1) + 'k';
          }
        },
        grid: { color: colors.grid }
      },
      x: {
        ticks: {
          color: colors.tick,
          maxTicksLimit: 10,
          font: { size: 9 }
        },
        grid: { display: false }
      }
    }
  }
});

// 7. Year-wise Income and Expense
new Chart(document.getElementById('yearWiseChart'), {
  type: 'bar',
  data: {
    labels: year_wise_data.label,
    datasets: [
      {
        label: 'Income',
        data: year_wise_data.income,
        backgroundColor: colors.income,
        borderRadius: 8
      },
      {
        label: 'Expense',
        data: year_wise_data.expense,
        backgroundColor: colors.expense,
        borderRadius: 8
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          color: colors.legend
        }
      },
      tooltip: currencyFormatter
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          color: colors.tick,
          callback: function (value) {
            return '₹' + (value / 1000).toFixed(0) + 'k';
          }
        },
        grid: { color: colors.grid }
      },
      x: {
        ticks: { color: colors.tick },
        grid: { display: false }
      }
    }
  }
});

// ============================================================================
// Remove loading states after all charts are rendered
// ============================================================================
removeLoadingStates();
