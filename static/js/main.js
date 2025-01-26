document.getElementById('news-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch('/predict', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        alert('检测功能待实现');
    })
    .catch(error => {
        console.error('Error:', error);
        alert('发生错误，请稍后重试');
    });
});

// 操作指南确认处理
document.getElementById('confirm-guide')?.addEventListener('click', function() {
    fetch('/confirm_guide', {
        method: 'POST',
    })
    .then(response => response.json())
    .then(data => {
        if(data.status === 'success') {
            document.getElementById('guide-modal').style.display = 'none';
        }
    });
});