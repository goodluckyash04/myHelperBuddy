// Extract data from Django template
const category_wise_data = data.category_wise_data;
const savings = data.savings;
const year_wise_data = data.year_wise_data;
const category_wise_month = data.category_wise_month;
const monthly_cash_flow = data.monthly_cash_flow;
const monthly_savings_rate = data.monthly_savings_rate;
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
    aspectRatio: window.innerWidth < 768 ? 1.6 : 2,
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

// 6. Monthly Savings Rate by Year
if (!monthly_savings_rate || !monthly_savings_rate.years || monthly_savings_rate.years.length === 0) {
  showEmptyState('monthlySavingsRateChart', 'No savings data available yet', 'fa-piggy-bank');
} else {
  // Generate datasets dynamically based on years present
  const datasets = [];
  const barColors = [
    'rgba(176, 163, 111, 0.4)',  // Oldest
    'rgba(176, 163, 111, 0.7)',
    'rgba(176, 163, 111, 1)'     // Newest
  ];
  
  monthly_savings_rate.years.forEach((year, index) => {
    datasets.push({
      type: 'bar',
      label: year.toString(),
      data: monthly_savings_rate.by_year[year],
      backgroundColor: barColors[barColors.length - monthly_savings_rate.years.length + index] || barColors[0],
      borderRadius: 4,
      barPercentage: 0.7,
      categoryPercentage: 0.8
    });
  });

  // Add all-time average line
  datasets.push({
    type: 'line',
    label: 'All-time Avg',
    data: monthly_savings_rate.all_time_avg,
    borderColor: colors.expense, // Reference/benchmark color
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderDash: [5, 4],
    pointRadius: 3,
    pointHoverRadius: 5,
    pointBackgroundColor: colors.expense,
    pointBorderColor: '#fff',
    tension: 0.3
  });

  new Chart(document.getElementById('monthlySavingsRateChart'), {
    data: {
      labels: monthly_savings_rate.months,
      datasets: datasets
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
            font: { size: 10 }
          }
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null && context.parsed.y !== undefined) {
                label += context.parsed.y + '%';
              }
              return label;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function (value) {
              return value + '%';
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
}

// 7. Year-wise Income and Expense
new Chart(document.getElementById('yearWiseChart'), {
  type: 'bar',
  data: {
    labels: year_wise_data.label,
    datasets: [
      {
        label: 'Income',
        data: year_wise_data.income,
        backgroundColor: colors.primary,
        borderRadius: 8
      },
      {
        label: 'Expense',
        data: year_wise_data.expense,
        backgroundColor: 'rgba(176, 163, 111, 0.4)',
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

// ============================================================================
// Remove loading states after all charts are rendered
// ============================================================================
removeLoadingStates();
