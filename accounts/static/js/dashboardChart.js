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

// Color palette
const colors = {
  income: '#10b981',
  expense: '#ef4444',
  savings: '#3b82f6',
  primary: 'rgba(176, 163, 111, 1)',
  primaryLight: 'rgba(176, 163, 111, 0.2)',
  categories: [
    '#f76c5e', '#a1e6c6', '#9b7bbf', '#f1c40f', '#1abc9c',
    '#e67e22', '#7f8c8d', '#d1b2a1', '#f5a623', '#8e8b3b'
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
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          font: { size: 12 }
        }
      },
      tooltip: currencyFormatter
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: function (value) {
            return '₹' + value.toLocaleString('en-IN');
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      },
      x: {
        grid: {
          display: false
        }
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
      borderColor: '#fff'
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
          font: {
            size: window.innerWidth < 768 ? 9 : 11
          },
          generateLabels: function (chart) {
            const data = chart.data;
            if (data.labels.length && data.datasets.length) {
              return data.labels.map((label, i) => {
                const value = data.datasets[0].data[i];
                const formattedValue = '₹' + (value / 1000).toFixed(1) + 'k';
                return {
                  text: window.innerWidth < 768 ? label.substring(0, 10) : `${label}: ${formattedValue}`,
                  fillStyle: data.datasets[0].backgroundColor[i],
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

// 5. Income Sources Chart
if (income_sources.labels && income_sources.labels.length > 0) {
  new Chart(document.getElementById('incomeSourcesChart'), {
    type: 'doughnut',
    data: {
      labels: income_sources.labels,
      datasets: [{
        data: income_sources.amounts,
        backgroundColor: [
          '#3b82f6',
          '#8b5cf6',
          '#ec4899',
          '#f43f5e',
          '#f97316'
        ],
        borderWidth: 2,
        borderColor: '#fff'
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
            font: {
              size: window.innerWidth < 768 ? 9 : 11
            },
            generateLabels: function (chart) {
              const data = chart.data;
              if (data.labels.length && data.datasets.length) {
                return data.labels.map((label, i) => {
                  const value = data.datasets[0].data[i];
                  const formattedValue = '₹' + (value / 1000).toFixed(1) + 'k';
                  return {
                    text: window.innerWidth < 768 ? label.substring(0, 10) : `${label}: ${formattedValue}`,
                    fillStyle: data.datasets[0].backgroundColor[i],
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
} else {
  // Show "No data" message
  const canvas = document.getElementById('incomeSourcesChart');
  const parent = canvas.parentElement;
  parent.innerHTML = '<div class="text-center text-muted py- 5"><i class="fa-solid fa-inbox fa-2x mb-2"></i><p>No income data</p></div>';
}

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
          callback: function (value) {
            return '₹' + (value / 1000).toFixed(1) + 'k';
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      },
      x: {
        ticks: {
          maxTicksLimit: 10,
          font: { size: 9 }
        },
        grid: {
          display: false
        }
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
          padding: 15
        }
      },
      tooltip: currencyFormatter
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: function (value) {
            return '₹' + (value / 1000).toFixed(0) + 'k';
          }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      },
      x: {
        grid: {
          display: false
        }
      }
    }
  }
});
