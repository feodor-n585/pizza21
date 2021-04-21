    print("Очищаем корзину")
    basket = Basket.query.all()
    try:
        for i in basket:
            db.session.delete(i)
        db.session.commit()
        # return redirect('/')
    except:
        return "Произошла ошибка очистки корзины"
