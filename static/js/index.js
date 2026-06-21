document.getElementById('contactForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    console.log("Але")
    const form = e.target;
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');
    const formMessage = document.getElementById('formMessage');
    
    // Собираем данные формы
    const formData = {
        name: document.getElementById('name').value.trim(),
        email: document.getElementById('email').value.trim(),
        phone: document.getElementById('phone').value.trim(),
        message: document.getElementById('message').value.trim()
    };
    
    // Валидация на клиенте
    if (!formData.name || !formData.email || !formData.message) {
        showMessage('Пожалуйста, заполните все обязательные поля', 'error');
        return;
    }
    
    // Показываем loader
    submitBtn.disabled = true;
    btnText.classList.add('hidden');
    btnLoader.classList.remove('hidden');

    console.log("Але")
    
    try {
        // Отправляем запрос
        const response = await fetch('/api/contact', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage(data.message, 'success');
            form.reset();
        } else if (response.status === 429) {
            showMessage(data.message, 'error');
        } else if (response.status === 400) {
            showMessage( data.message, 'error');
        } else {
            showMessage('Произошла ошибка. Попробуйте позже.', 'error');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showMessage('Ошибка соединения с сервером', 'error');
    } finally {
        // Скрываем loader
        submitBtn.disabled = false;
        btnText.classList.remove('hidden');
        btnLoader.classList.add('hidden');
    }
});

// Проверка чекбокса перед отправкой формы
document.getElementById('contactForm').addEventListener('submit', function(e) {
    const privacyConsent = document.getElementById('privacyConsent');
    const formMessage = document.getElementById('formMessage');
    
    if (!privacyConsent.checked) {
        e.preventDefault();
        formMessage.classList.remove('hidden', 'bg-green-500/20', 'text-green-100');
        formMessage.classList.add('bg-red-500/20', 'text-red-100');
        formMessage.innerHTML = '<i class="fas fa-exclamation-circle mr-2"></i>Пожалуйста, подтвердите согласие на обработку персональных данных';
        
        // Прокрутка к сообщению об ошибке
        formMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return false;
    }
    
    // Если чекбокс отмечен, форма отправляется (здесь должна быть ваша логика отправки)
    // Очистка предыдущих сообщений
    formMessage.classList.add('hidden');
});

// Очистка сообщения об ошибке при изменении чекбокса
document.getElementById('privacyConsent').addEventListener('change', function() {
    const formMessage = document.getElementById('formMessage');
    if (this.checked) {
        formMessage.classList.add('hidden');
    }
});

function showMessage(text, type) {
    const formMessage = document.getElementById('formMessage');
    formMessage.textContent = text;
    formMessage.classList.remove('hidden', 'bg-green-500', 'bg-red-500');
    
    if (type === 'success') {
        formMessage.classList.add('bg-green-500');
    } else {
        formMessage.classList.add('bg-red-500');
    }
    
    // Скрываем сообщение через 5 секунд
    setTimeout(() => {
        formMessage.classList.add('hidden');
    }, 5000);
}