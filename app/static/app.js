const toast = (message, isError = false) => {
  const node = document.querySelector('#toast')
  if (!node) return
  node.textContent = message
  node.classList.toggle('toast-error', isError)
  node.classList.add('show')
  window.clearTimeout(window.toastTimeout)
  window.toastTimeout = window.setTimeout(() => node.classList.remove('show'), 3600)
}

const requestJson = async (url, options = {}) => {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || 'Something went wrong. Please try again.')
  return body
}

const money = (amount, currency) => new Intl.NumberFormat(undefined, { style: 'currency', currency, maximumFractionDigits: 0 }).format(amount)

const form = document.querySelector('#event-form')
if (form) {
  const steps = [...form.querySelectorAll('.form-step')]
  const indicators = [...document.querySelectorAll('.wizard-progress i')]
  const captions = ['The occasion', 'The details', 'The feeling', 'Your review']
  let currentStep = 0
  const showStep = index => {
    currentStep = index
    steps.forEach((step, i) => step.classList.toggle('active', i === index))
    indicators.forEach((item, i) => item.classList.toggle('active', i <= index))
    document.querySelector('#step-caption').textContent = `0${index + 1} / 04`
    document.querySelector('#step-name').textContent = captions[index]
    document.querySelector('#prev-step').classList.toggle('invisible', index === 0)
    document.querySelector('#next-step').classList.toggle('hidden', index === steps.length - 1)
    document.querySelector('#generate-plan').classList.toggle('hidden', index !== steps.length - 1)
    if (index === steps.length - 1) renderReview()
    document.querySelector('#form-error').textContent = ''
  }
  const currentFields = () => [...steps[currentStep].querySelectorAll('input,select,textarea')]
  const validate = () => {
    const fields = currentFields()
    for (const field of fields) {
      if (field.type === 'radio') {
        if (!form.querySelector(`input[name="${field.name}"]:checked`)) {
          document.querySelector('#form-error').textContent = 'Choose the occasion you’re celebrating.'
          return false
        }
        continue
      }
      if (!field.checkValidity()) {
        field.reportValidity()
        return false
      }
    }
    return true
  }
  const renderReview = () => {
    const data = new FormData(form)
    const entries = [
      ['Occasion', data.get('event_type')], ['Event name', data.get('name')], ['Date', data.get('event_date')], ['Location', data.get('location')],
      ['Guests', data.get('guests')], ['Budget', `${data.get('currency')} ${Number(data.get('budget')).toLocaleString()}`], ['Style', data.get('style')],
      ['Food', data.get('food_preference')], ['Priority', data.get('priority')], ['Notes', data.get('notes') || 'None']
    ]
    document.querySelector('#review-card').innerHTML = entries.map(([label, value]) => `<div class="review-item"><small>${label}</small><b>${escapeHtml(value)}</b></div>`).join('')
  }
  document.querySelector('#next-step').addEventListener('click', () => { if (validate()) showStep(Math.min(currentStep + 1, steps.length - 1)) })
  document.querySelector('#prev-step').addEventListener('click', () => showStep(Math.max(currentStep - 1, 0)))
  form.addEventListener('submit', async event => {
    event.preventDefault()
    const button = document.querySelector('#generate-plan')
    const error = document.querySelector('#form-error')
    button.disabled = true
    button.innerHTML = '<span class="spinner"></span> Creating your plan…'
    error.textContent = ''
    try {
      const data = Object.fromEntries(new FormData(form).entries())
      const result = await requestJson('/api/events', { method: 'POST', body: JSON.stringify(data) })
      window.location.assign(result.redirect)
    } catch (err) {
      error.textContent = err.message
      button.disabled = false
      button.innerHTML = 'Generate my plan <span>✦</span>'
    }
  })
}

const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character])

const dashboard = document.querySelector('#dashboard')
if (dashboard) {
  const eventId = dashboard.dataset.eventId
  const eventData = JSON.parse(document.querySelector('#event-plan-data')?.textContent || 'null')
  const budgetRows = [...document.querySelectorAll('.budget-amount')]
  const allocated = budgetRows.reduce((sum, row) => sum + Number(row.dataset.amount), 0)
  const total = Number(eventData?.budget || 0)
  if (eventData) {
    const currency = eventData.currency
    document.querySelector('#allocated-stat').textContent = money(allocated, currency)
    document.querySelector('#remaining-stat').textContent = money(total - allocated, currency)
    document.querySelector('#donut-total').textContent = money(total, currency)
    const remainingNote = document.querySelector('#remaining-note')
    if (allocated > total) {
      remainingNote.textContent = 'Planned spending is over budget'
      remainingNote.classList.add('over-budget')
      document.querySelector('#budget-alert').classList.remove('hidden')
    }
    const days = Math.ceil((new Date(`${eventData.event_date}T00:00:00`) - new Date(new Date().toDateString())) / 86400000)
    document.querySelector('#days-stat').textContent = days > 0 ? `${days} days` : days === 0 ? 'Today!' : 'Celebrated'
    const categories = eventData.plan.budget.categories
    const colors = ['#8267c8', '#e99a83', '#e8c46c', '#82a68c', '#d786a2', '#6da9a5', '#b09671', '#a5a0b8']
    document.querySelector('#budget-legend').innerHTML = categories.map((item, i) => `<span><i style="background:${colors[i % colors.length]}"></i>${escapeHtml(item.category)}</span>`).join('')
    document.querySelector('#donut-chart').style.background = `conic-gradient(${categories.map((item, i) => {
      const preceding = categories.slice(0, i).reduce((sum, category) => sum + Number(category.amount), 0) / total * 100
      const end = preceding + Number(item.amount) / total * 100
      return `${colors[i % colors.length]} ${preceding}% ${end}%`
    }).join(',')}, #f0eeeb ${Math.min(100, allocated / total * 100)}% 100%)`
  }
  const updateProgress = () => {
    const tasks = [...document.querySelectorAll('[data-task-id]')]
    const completed = tasks.filter(item => item.checked).length
    const percent = tasks.length ? Math.round(completed / tasks.length * 100) : 0
    document.querySelector('#progress-percent').textContent = `${percent}%`
    document.querySelector('#progress-bar').style.width = `${percent}%`
    document.querySelector('#progress-complete').textContent = `${completed} of ${tasks.length} tasks done`
  }
  document.querySelectorAll('[data-task-id]').forEach(input => input.addEventListener('change', async () => {
    try {
      await requestJson(`/api/tasks/${input.dataset.taskId}`, { method: 'PATCH', body: JSON.stringify({ status: input.checked ? 'completed' : 'pending' }) })
      input.closest('.timeline-item,.next-row')?.classList.toggle('is-complete', input.checked)
      updateProgress()
      toast(input.checked ? 'A little win, checked off.' : 'Task moved back to your list.')
    } catch (err) { input.checked = !input.checked; toast(err.message, true) }
  }))
  updateProgress()
  document.querySelectorAll('.vendor-status').forEach(select => select.addEventListener('change', async () => {
    try {
      await requestJson(`/api/vendors/${select.dataset.vendorId}`, { method: 'PATCH', body: JSON.stringify({ status: select.value }) })
      toast('Vendor status saved.')
    } catch (err) { toast(err.message, true) }
  }))
  const aiRequest = async (action, message) => {
    const result = await requestJson(`/api/events/${eventId}/ai`, { method: 'POST', body: JSON.stringify({ action, message }) })
    if (action === 'chat') appendMessage('planner', result.answer)
    if (action === 'ideas') {
      const list = document.querySelector('#idea-list')
      list.innerHTML = result.ideas.map(item => `<article class="idea-card"><div class="idea-top"><span class="idea-spark">✳</span><span class="cost-chip">${escapeHtml(item.cost_level)}</span></div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.description)}</p><div class="idea-fit"><span>WHY IT FITS</span><p>${escapeHtml(item.reason)}</p></div></article>`).join('')
      toast('Fresh ideas, just for your day.')
    }
    if (action === 'optimize') {
      document.querySelector('#budget-alert').classList.add('hidden')
      toast('Your optimized budget is ready. Refresh to see the updated allocations.')
      window.location.reload()
    }
  }
  const appendMessage = (speaker, text) => {
    const log = document.querySelector('#chat-log')
    const bubble = document.createElement('div')
    bubble.className = `chat-message ${speaker}`
    bubble.textContent = text
    log.append(bubble)
    log.scrollTop = log.scrollHeight
  }
  document.querySelectorAll('[data-ai-action]').forEach(button => button.addEventListener('click', async () => {
    const action = button.dataset.aiAction
    const message = button.dataset.message || (action === 'optimize' ? '' : '')
    button.disabled = true
    const original = button.innerHTML
    button.innerHTML = '<span class="spinner"></span> Thinking…'
    if (action === 'chat') appendMessage('user', message)
    try { await aiRequest(action, message) } catch (err) { if (action === 'chat') appendMessage('planner', err.message); else toast(err.message, true) }
    button.disabled = false
    button.innerHTML = original
  }))
  document.querySelector('#chat-form').addEventListener('submit', async event => {
    event.preventDefault()
    const input = document.querySelector('#chat-message')
    const message = input.value.trim()
    if (!message) return
    appendMessage('user', message)
    input.value = ''
    try { await aiRequest('chat', message) } catch (err) { appendMessage('planner', err.message) }
  })
  document.querySelector('#guest-form').addEventListener('submit', async event => {
    event.preventDefault()
    const data = Object.fromEntries(new FormData(event.currentTarget).entries())
    try {
      const result = await requestJson(`/api/guests/${eventId}`, { method: 'PATCH', body: JSON.stringify(data) })
      document.querySelector('#guest-groups').innerHTML = result.categories.map(item => `<div class="guest-group"><b>${escapeHtml(item.category)}</b><span>${item.confirmed} confirmed / ${item.estimated} estimated</span><small>${item.estimated - item.confirmed} pending</small></div>`).join('')
      toast('Guest group saved.')
    } catch (err) { toast(err.message, true) }
  })
  const sections = [...document.querySelectorAll('.dash-section[id]')]
  const navLinks = [...document.querySelectorAll('.side-link')]
  const observer = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) navLinks.forEach(link => link.classList.toggle('active', link.hash === `#${entry.target.id}`))
  }), { rootMargin: '-20% 0px -70% 0px' })
  sections.forEach(section => observer.observe(section))
}
