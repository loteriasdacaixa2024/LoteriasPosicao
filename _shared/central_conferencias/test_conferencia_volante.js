const assert = require('assert');
const Sim = require('./static/js/conferencia-volante.js');

const sorteio = [1, 2, 3, 4, 5, 6, 7];
const apostaA = [1, 2, 3, 4, 10, 11, 12];
const apostaB = [5, 6, 13, 14, 15, 16, 17];

const confA = Sim.conferirDezenas(apostaA, sorteio);
assert.strictEqual(confA.acertos, 4);
assert.deepStrictEqual(confA.coincidentes, [1, 2, 3, 4]);
assert.deepStrictEqual(confA.soSorteio, [5, 6, 7]);
assert.strictEqual(confA.apostadas.length, 7);

const dup = Sim.dezenasValidas([1, 1, 2, 3, 4, 5, 6, 7]);
assert.deepStrictEqual(dup.duplicadas, [1]);
assert.strictEqual(dup.completa, false);

assert.strictEqual(Sim.mesesIguais('Jan', 'janeiro'), true);
assert.strictEqual(Sim.mesesIguais('Set', 'Out'), false);
assert.strictEqual(Sim.conferirDezenas(apostaA, sorteio).acertos, 4);

const p4 = Sim.premiacaoFixa(4, false);
assert.strictEqual(p4.total, 5);
assert.strictEqual(p4.incompleto, false);

const p5 = Sim.premiacaoFixa(5, true);
assert.strictEqual(p5.total, 27.5);

const p6 = Sim.premiacaoFixa(6, true);
assert.strictEqual(p6.incompleto, true);
assert.ok(p6.partes.some(p => p.valor == null));
assert.ok(!p6.partes.some(p => p.valor === 25));

const p6sem = Sim.premiacaoFixa(6, false);
assert.strictEqual(p6sem.total, 5);
assert.strictEqual(p6sem.incompleto, false);

const sim = Sim.simular([apostaA, apostaB], sorteio, { limite: 20 });
assert.strictEqual(sim.melhorOriginal, 4);
assert.deepStrictEqual(sim.furos, [7]);
assert.strictEqual(sim.acertaveis.length, 6);
assert.ok(sim.combinacoes.length > 0);
const chaves = new Set();
sim.combinacoes.forEach(c => {
    assert.strictEqual(c.nums.length, 7);
    assert.strictEqual(new Set(c.nums).size, 7);
    c.nums.forEach(n => {
        assert.ok(n >= 1 && n <= 31);
        assert.ok(sim.uniao.includes(n));
    });
    const key = c.nums.join(',');
    assert.ok(!chaves.has(key));
    chaves.add(key);
    assert.strictEqual(c.acertos, Sim.conferirDezenas(c.nums, sorteio).acertos);
    assert.strictEqual(c.acertos, 6);
    assert.strictEqual(c.delta, 2);
});

const fora = Sim.simular([apostaA, apostaB], sorteio, { incluirFora: true, limite: 12 });
assert.ok(fora.combinacoesFora.length > 0);
fora.combinacoesFora.forEach(c => {
    assert.ok(c.foraDasApostas.includes(7));
    assert.ok(c.acertos >= 6);
});

const vazio = Sim.simular([], sorteio);
assert.strictEqual(vazio.podeFormar, false);
assert.deepStrictEqual(vazio.combinacoes, []);

const dist = Sim.distribuicao([
    { idx: 0, id: 1, acertos: 4 },
    { idx: 1, id: 2, acertos: 4 },
    { idx: 2, id: 3, acertos: 1 },
]);
assert.strictEqual(dist.max, 4);
assert.strictEqual(dist.melhores.length, 2);
assert.strictEqual(dist.concentrado, false);

const unico = Sim.distribuicao([{ idx: 0, id: 7, acertos: 4 }, { idx: 1, id: 8, acertos: 0 }]);
assert.strictEqual(unico.concentrado, true);
assert.strictEqual(unico.melhores[0].id, 7);

const resumo = Sim.resumoConcursos(
    [
        { id: 1, nums: apostaA, mes: 'Jan' },
        { id: 2, nums: apostaB, mes: 'Fev' },
    ],
    [
        { concurso: 10, data: '01/01/2020', dezenas: sorteio, mes: 'Jan' },
        { concurso: 9, data: '01/12/2019', dezenas: [8, 9, 10, 11, 12, 13, 14], mes: 'Mar' },
    ]
);
assert.strictEqual(resumo.length, 2);
assert.strictEqual(resumo[0].acertos, 4);
assert.strictEqual(resumo[0].mesEntrou, true);
assert.strictEqual(resumo[0].simAcertos, 6);
assert.strictEqual(resumo[0].delta, 2);
assert.strictEqual(resumo[0].totalApostas, 2);
assert.strictEqual(resumo[1].mesEntrou, false);

console.log('conferencia-volante: ok');
